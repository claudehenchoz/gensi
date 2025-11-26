"""Main processor for orchestrating .gensi file processing into EPUB."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass
from slugify import slugify

from .parser import GensiParser
from .cached_fetcher import CachedFetcher
from .extractor import Extractor, parse_rss_feed, parse_bluesky_feed
from .sanitizer import Sanitizer
from .python_executor import PythonExecutor
from .epub_builder import EPUBBuilder
from .image_processor import process_article_images
from .image_optimizer import process_image
from .typography import improve_typography
from .replacements import apply_replacements
from .cover_generator import CoverGenerator
from ..utils.thumbnail_extractor import extract_thumbnails
from lxml import html as lxml_html

logger = logging.getLogger(__name__)


@dataclass
class ProcessingProgress:
    """Progress information for processing."""
    stage: str  # 'parsing', 'cover', 'index', 'article', 'building', 'done'
    current: int = 0
    total: int = 0
    message: str = ''


class GensiProcessor:
    """Main processor for .gensi files."""

    def __init__(
        self,
        gensi_path: Path | str,
        output_dir: Optional[Path | str] = None,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
        max_parallel: int = 5,
        cache_enabled: bool = True
    ):
        """
        Initialize the processor.

        Args:
            gensi_path: Path to the .gensi file
            output_dir: Output directory for the EPUB (default: same as .gensi file)
            progress_callback: Callback function for progress updates
            max_parallel: Maximum number of parallel downloads (default: 5)
            cache_enabled: Whether to enable HTTP caching (default: True)
        """
        self.gensi_path = Path(gensi_path)
        self.output_dir = Path(output_dir) if output_dir else self.gensi_path.parent
        self.progress_callback = progress_callback
        self.max_parallel = max_parallel
        self.cache_enabled = cache_enabled

        self.parser: Optional[GensiParser] = None
        self.sanitizer = Sanitizer()
        self.python_executor = PythonExecutor()
        self.cover_data: Optional[bytes] = None
        self.cover_extension: Optional[str] = None

    def _report_progress(self, stage: str, current: int = 0, total: int = 0, message: str = ''):
        """Report progress to the callback."""
        if self.progress_callback:
            self.progress_callback(ProcessingProgress(stage, current, total, message))

    async def process(self) -> Path:
        """
        Process the .gensi file and generate an EPUB.

        Returns:
            Path to the generated EPUB file

        Raises:
            Exception: If processing fails
        """
        try:
            # Parse .gensi file
            self._report_progress('parsing', message='Parsing .gensi file')
            self.parser = GensiParser(self.gensi_path)

            # Process cover
            if self.parser.cover:
                await self._process_cover()

            # Process indices and articles
            sections_data = []
            total_articles = 0

            # First pass: collect all articles
            async with CachedFetcher(cache_enabled=self.cache_enabled) as fetcher:
                for i, index_config in enumerate(self.parser.indices):
                    # Use name if provided, otherwise None (for single index case)
                    section_name = index_config.get('name')
                    if section_name:
                        self._report_progress('index', message=f'Processing index: {section_name}')
                    else:
                        self._report_progress('index', message='Processing articles')

                    articles = await self._process_index(fetcher, index_config)
                    total_articles += len(articles)

                    sections_data.append({
                        'name': section_name,
                        'articles': articles,
                        'index': i  # Store index to match later
                    })

                # Second pass: fetch and process articles in parallel
                current_article = 0
                for section in sections_data:
                    # Get article config for this section's index
                    index_config = self.parser.indices[section['index']]
                    article_config = self.parser.get_article_config(index_config)

                    # Process articles with parallel limit
                    semaphore = asyncio.Semaphore(self.max_parallel)

                    async def process_article_with_limit(article_data):
                        nonlocal current_article
                        async with semaphore:
                            current_article += 1
                            self._report_progress(
                                'article',
                                current=current_article,
                                total=total_articles,
                                message=f'Downloading article {current_article}/{total_articles}'
                            )
                            return await self._process_article(fetcher, article_data, article_config)

                    # Process all articles in section
                    processed_articles = await asyncio.gather(
                        *[process_article_with_limit(art) for art in section['articles']]
                    )
                    section['articles'] = processed_articles

                # Generate automatic cover if no explicit cover was provided
                if not self.parser.cover and not self.cover_data:
                    await self._generate_auto_cover(sections_data)

            # Build EPUB
            self._report_progress('building', message='Building EPUB file')
            output_path = await self._build_epub(sections_data)

            self._report_progress('done', message=f'EPUB created: {output_path.name}')
            return output_path

        except Exception as e:
            self._report_progress('error', message=f'Error: {str(e)}')
            raise

    async def _process_cover(self) -> None:
        """Process and fetch the cover image."""
        cover_config = self.parser.cover
        if not cover_config:
            return

        self._report_progress('cover', message='Downloading cover image')

        async with CachedFetcher(cache_enabled=self.cache_enabled) as fetcher:
            # Fetch cover page/image
            cover_url = cover_config['url']
            from ..utils.url_utils import is_image_url

            if is_image_url(cover_url):
                # Direct image URL
                raw_data, _ = await fetcher.fetch_binary(cover_url, context="cover")
                # Process cover image (resize and optimize)
                try:
                    self.cover_data, self.cover_extension = process_image(
                        raw_data, cover_url, image_type='cover'
                    )
                except Exception as e:
                    logger.warning(f"Failed to process cover image {cover_url}: {e}")
                    # Fallback to raw data
                    self.cover_data = raw_data
                    # Try to extract extension from URL
                    from ..utils.url_utils import is_image_url
                    from pathlib import Path
                    from urllib.parse import urlparse
                    parsed = urlparse(cover_url)
                    ext = Path(parsed.path).suffix.lstrip('.')
                    self.cover_extension = ext if ext else 'jpg'
            else:
                # Page with image
                html_content, final_url = await fetcher.fetch(cover_url, context="cover")
                extractor = Extractor(final_url, html_content)
                cover_img_url = extractor.extract_cover_url(cover_config, self.python_executor)

                if cover_img_url:
                    raw_data, _ = await fetcher.fetch_binary(cover_img_url, context="cover")
                    # Process cover image (resize and optimize)
                    try:
                        self.cover_data, self.cover_extension = process_image(
                            raw_data, cover_img_url, image_type='cover'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to process cover image {cover_img_url}: {e}")
                        # Fallback to raw data
                        self.cover_data = raw_data
                        # Try to extract extension from URL
                        from pathlib import Path
                        from urllib.parse import urlparse
                        parsed = urlparse(cover_img_url)
                        ext = Path(parsed.path).suffix.lstrip('.')
                        self.cover_extension = ext if ext else 'jpg'

    async def _generate_auto_cover(self, sections_data: list[dict]) -> None:
        """
        Generate cover automatically from article thumbnails.

        Args:
            sections_data: Processed sections with articles containing thumbnails
        """
        self._report_progress('cover', message='Generating automatic cover')

        # Collect thumbnails from all articles
        thumbnail_urls = []
        for section in sections_data:
            for article in section['articles']:
                thumbnail = article.get('thumbnail')
                if thumbnail:
                    thumbnail_urls.append(thumbnail)

        # Deduplicate while preserving order, limit to 6
        seen = set()
        unique_thumbnails = []
        for url in thumbnail_urls:
            if url not in seen:
                seen.add(url)
                unique_thumbnails.append(url)
        unique_thumbnails = unique_thumbnails[:6]

        logger.info(f"Auto-cover: Found {len(unique_thumbnails)} unique thumbnails")

        if not unique_thumbnails:
            logger.info("Auto-cover: No thumbnails found, generating text-only cover")

        # Generate cover
        try:
            async with CachedFetcher(cache_enabled=self.cache_enabled) as fetcher:
                generator = CoverGenerator()
                cover_data, cover_ext = await generator.generate_from_thumbnails(
                    thumbnail_urls=unique_thumbnails,
                    title=self.parser.title,
                    author=self.parser.author,
                    fetcher=fetcher,
                    fallback_to_text=True
                )

                self.cover_data = cover_data
                self.cover_extension = cover_ext
                logger.info(f"Auto-cover: Generated ({len(cover_data)} bytes, .{cover_ext})")

        except Exception as e:
            logger.warning(f"Auto-cover generation failed: {e}")
            # Don't raise - it's OK to have no cover

    async def _process_index(self, fetcher: CachedFetcher, index_config: dict) -> list[dict]:
        """
        Process an index to extract article URLs.

        Args:
            fetcher: The fetcher instance
            index_config: The index configuration

        Returns:
            List of article data dictionaries
        """
        index_url = index_config['url']
        index_type = index_config['type']

        if index_type == 'html':
            # Fetch HTML index (not cached due to context="index")
            html_content, final_url = await fetcher.fetch(index_url, context="index")

            # Check if response is actually JSON
            content_type = 'json' if index_config.get('response_type') == 'json' else 'html'
            extractor = Extractor(final_url, html_content, content_type=content_type, config=index_config)
            articles = extractor.extract_index_articles(index_config, self.python_executor)

            # Apply URL transformation if configured
            if 'url_transform' in index_config:
                for article in articles:
                    article['url'] = extractor.transform_url(
                        article['url'],
                        index_config['url_transform'],
                        self.python_executor
                    )

            return articles

        elif index_type == 'json':
            # Fetch JSON index (not cached due to context="index")
            json_content, final_url = await fetcher.fetch(index_url, context="index")
            extractor = Extractor(final_url, json_content, content_type='json', config=index_config)
            articles = extractor.extract_index_articles(index_config, self.python_executor)

            # Apply URL transformation if configured
            if 'url_transform' in index_config:
                for article in articles:
                    article['url'] = extractor.transform_url(
                        article['url'],
                        index_config['url_transform'],
                        self.python_executor
                    )

            return articles

        elif index_type == 'rss':
            # Fetch RSS/Atom feed (not cached due to context="index")
            feed_content, final_url = await fetcher.fetch(index_url, context="index")
            articles = parse_rss_feed(final_url, feed_content, index_config, self.python_executor)
            return articles

        elif index_type == 'bluesky':
            # Build Bluesky API URL
            username = index_config.get('username')
            limit = index_config.get('limit', 20)
            api_url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={username}&limit={limit}"

            # Fetch from API (not cached)
            json_content, final_url = await fetcher.fetch(api_url, context="index")
            articles = parse_bluesky_feed(final_url, json_content, index_config, self.python_executor)
            return articles

        else:
            raise ValueError(f"Unknown index type: {index_type}")

    async def _process_article(
        self,
        fetcher: CachedFetcher,
        article_data: dict,
        article_config: Optional[dict]
    ) -> dict:
        """
        Process a single article.

        Args:
            fetcher: The fetcher instance
            article_data: Article data with 'url' and optional 'content'
            article_config: The article configuration

        Returns:
            Processed article data with 'content', 'title', 'author', 'date'
        """
        # If content already provided, sanitize and return
        if 'content' in article_data and article_data['content']:
            sanitized_content = self.sanitizer.sanitize(article_data['content'])
            # Improve typography
            sanitized_content = improve_typography(sanitized_content)
            # Apply replacements
            sanitized_content = apply_replacements(sanitized_content, self.parser.replacements)
            # Process images (check config for images setting, default to True)
            article_url = article_data['url']
            enable_images = article_config.get('images', True) if article_config else True
            sanitized_content, image_map = await process_article_images(
                sanitized_content, article_url, fetcher, enable_images, image_type='article'
            )

            # Extract thumbnail for potential cover generation
            thumbnail = None
            try:
                doc = lxml_html.fromstring(sanitized_content)
                thumbnails = extract_thumbnails(doc, article_url, max_count=1)
                thumbnail = thumbnails[0] if thumbnails else None
            except Exception as e:
                logger.debug(f"Failed to extract thumbnail from {article_url}: {e}")

            return {
                'url': article_url,
                'content': sanitized_content,
                'title': article_data.get('title'),
                'author': article_data.get('author'),
                'date': article_data.get('date'),
                'images': image_map,
                'thumbnail': thumbnail
            }

        # Fetch article
        article_url = article_data['url']
        content, final_url = await fetcher.fetch(article_url, context="article")

        # Extract thumbnail from ORIGINAL full HTML (before content extraction strips meta tags)
        thumbnail = None
        try:
            doc = lxml_html.fromstring(content)
            thumbnails = extract_thumbnails(doc, final_url, max_count=1)
            thumbnail = thumbnails[0] if thumbnails else None
        except Exception as e:
            logger.debug(f"Failed to extract thumbnail from {final_url}: {e}")

        # Extract content
        if article_config:
            # Determine content type
            content_type = 'json' if article_config.get('response_type') == 'json' else 'html'
            extractor = Extractor(final_url, content, content_type=content_type, config=article_config)
            extracted = extractor.extract_article_content(article_config, self.python_executor)

            # Sanitize content
            if extracted['content']:
                sanitized = self.sanitizer.sanitize(extracted['content'])
                # Check if sanitization left us with empty content
                if not sanitized or not sanitized.strip():
                    # Fallback: wrap original content in a div and try again
                    wrapped = f"<div>{extracted['content']}</div>"
                    sanitized = self.sanitizer.sanitize(wrapped)
                    if not sanitized or not sanitized.strip():
                        # Last resort: use a placeholder
                        sanitized = f"<p>Content could not be sanitized from {article_url}</p>"

                # Improve typography
                sanitized = improve_typography(sanitized)

                # Apply replacements
                sanitized = apply_replacements(sanitized, self.parser.replacements)

                # Process images (download and update references)
                enable_images = article_config.get('images', True) if article_config else True
                sanitized, image_map = await process_article_images(
                    sanitized, final_url, fetcher, enable_images, image_type='article'
                )

                extracted['content'] = sanitized
                extracted['images'] = image_map  # Store image data
                extracted['thumbnail'] = thumbnail  # Use thumbnail extracted from full HTML
            else:
                extracted['images'] = {}
                extracted['thumbnail'] = thumbnail  # Use thumbnail extracted from full HTML

            return extracted
        else:
            # No article config - return minimal data
            return {
                'url': article_url,
                'content': f'<p>No article configuration provided for {article_url}</p>',
                'title': article_url,
                'author': None,
                'date': None,
                'images': {},
                'thumbnail': thumbnail  # Use thumbnail extracted from full HTML
            }

    async def _build_epub(self, sections_data: list[dict]) -> Path:
        """
        Build the EPUB file from processed sections and articles.

        Args:
            sections_data: List of sections with processed articles

        Returns:
            Path to the generated EPUB file
        """
        builder = EPUBBuilder(
            title=self.parser.title,
            author=self.parser.author,
            language=self.parser.language or 'en'
        )

        # Add cover if available
        if self.cover_data:
            cover_name = f"cover.{self.cover_extension}" if self.cover_extension else "cover.jpg"
            builder.add_cover(self.cover_data, cover_name)

        # Add sections and articles
        for section in sections_data:
            builder.add_section(section['name'])
            for article in section['articles']:
                builder.add_article(
                    content=article['content'],
                    title=article.get('title'),
                    author=article.get('author'),
                    date=article.get('date'),
                    images=article.get('images', {})
                )

        # Generate output path using slugify
        output_filename = f"{slugify(self.parser.title)}.epub"
        output_path = self.output_dir / output_filename

        # Build EPUB
        builder.build(output_path)

        return output_path


async def process_gensi_file(
    gensi_path: Path | str,
    output_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    max_parallel: int = 5,
    cache_enabled: bool = True
) -> Path:
    """
    Convenience function to process a .gensi file.

    Args:
        gensi_path: Path to the .gensi file
        output_dir: Output directory for the EPUB
        progress_callback: Callback function for progress updates
        max_parallel: Maximum number of parallel downloads
        cache_enabled: Whether to enable HTTP caching (default: True)

    Returns:
        Path to the generated EPUB file
    """
    processor = GensiProcessor(gensi_path, output_dir, progress_callback, max_parallel, cache_enabled)
    return await processor.process()
