"""Main processor for orchestrating .gensi file processing into EPUB."""

import asyncio
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass
from slugify import slugify

from .parser import GensiParser
from .cached_fetcher import CachedFetcher
from .extractor import Extractor, parse_rss_feed
from .sanitizer import Sanitizer
from .python_executor import PythonExecutor
from .epub_builder import EPUBBuilder
from .image_processor import process_article_images
from .typography import improve_typography


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
                self.cover_data, _ = await fetcher.fetch_binary(cover_url, context="cover")
            else:
                # Page with image
                html_content, final_url = await fetcher.fetch(cover_url, context="cover")
                extractor = Extractor(final_url, html_content)
                cover_img_url = extractor.extract_cover_url(cover_config, self.python_executor)

                if cover_img_url:
                    self.cover_data, _ = await fetcher.fetch_binary(cover_img_url, context="cover")

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
            # Process images (check config for images setting, default to True)
            article_url = article_data['url']
            enable_images = article_config.get('images', True) if article_config else True
            sanitized_content, image_map = await process_article_images(
                sanitized_content, article_url, fetcher, enable_images
            )
            return {
                'url': article_url,
                'content': sanitized_content,
                'title': article_data.get('title'),
                'author': article_data.get('author'),
                'date': article_data.get('date'),
                'images': image_map
            }

        # Fetch article
        article_url = article_data['url']
        content, final_url = await fetcher.fetch(article_url, context="article")

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

                # Process images (download and update references)
                enable_images = article_config.get('images', True) if article_config else True
                sanitized, image_map = await process_article_images(sanitized, final_url, fetcher, enable_images)

                extracted['content'] = sanitized
                extracted['images'] = image_map  # Store image data
            else:
                extracted['images'] = {}

            return extracted
        else:
            # No article config - return minimal data
            return {
                'url': article_url,
                'content': f'<p>No article configuration provided for {article_url}</p>',
                'title': article_url,
                'author': None,
                'date': None,
                'images': {}
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
            builder.add_cover(self.cover_data)

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
