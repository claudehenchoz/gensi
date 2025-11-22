"""Content extraction from HTML using lxml and CSS selectors."""

from typing import Any, Optional
from lxml import html, etree
import feedparser
import re
from ..utils.url_utils import resolve_url, resolve_urls_in_html
from ..utils.metadata_fallback import extract_metadata_fallback
from .json_utils import extract_json_path, extract_json_paths


class Extractor:
    """Extracts content from HTML and JSON using CSS selectors and Python scripts."""

    def __init__(self, base_url: str, content: str, content_type: str = 'html', config: dict[str, Any] = None):
        """
        Initialize the extractor.

        Args:
            base_url: The base URL for resolving relative URLs
            content: The content to parse (HTML string or JSON string)
            content_type: Type of content ('html' or 'json')
            config: Optional configuration with json_path for JSON extraction
        """
        self.base_url = base_url
        self.content = content
        self.content_type = content_type
        self.config = config or {}

        if content_type == 'json':
            # For JSON, extract HTML using json_path if available
            if 'json_path' in self.config:
                json_path = self.config['json_path']
                # Check if json_path is a string (extract HTML only) or dict (multiple fields)
                if isinstance(json_path, str):
                    html_content = extract_json_path(content, json_path)
                    self.html_content = html_content
                    self.document = html.fromstring(html_content)
                    self.json_data = None
                else:
                    # Dict mode - will be handled in extract_article_content
                    # For now, just store the JSON data
                    self.html_content = None
                    self.document = None
                    import json
                    self.json_data = json.loads(content)
            else:
                # JSON mode without json_path - will be handled by Python override
                self.html_content = None
                self.document = None
                import json
                self.json_data = json.loads(content)
        else:
            # HTML mode
            self.html_content = content
            self.document = html.fromstring(content)
            self.json_data = None

    def extract_cover_url(self, config: dict[str, Any], python_executor=None) -> Optional[str]:
        """
        Extract the cover image URL.

        Args:
            config: The cover configuration
            python_executor: Python executor instance for running scripts

        Returns:
            The cover image URL (absolute), or None if extraction fails
        """
        # Check if using Python override
        if 'python' in config and python_executor:
            result = python_executor.execute(config['python']['script'], {'document': self.document})
            if isinstance(result, str):
                return resolve_url(self.base_url, result)
            else:
                raise TypeError(f"Cover Python script must return string, got {type(result)}")

        # Simple mode
        url = config.get('url', '')
        from ..utils.url_utils import is_image_url

        # If URL points directly to an image, return it
        if is_image_url(url):
            return resolve_url(self.base_url, url)

        # Otherwise, use selector
        selector = config.get('selector')
        if not selector:
            raise ValueError("Cover: 'selector' is required when URL doesn't point to an image")

        try:
            img_elem = self.document.cssselect(selector)
            if img_elem and len(img_elem) > 0:
                src = img_elem[0].get('src', '')
                if src:
                    return resolve_url(self.base_url, src)
        except Exception as e:
            raise Exception(f"Failed to extract cover image: {str(e)}") from e

        return None

    def extract_index_articles(
        self, config: dict[str, Any], python_executor=None
    ) -> list[dict[str, Any]]:
        """
        Extract article URLs from an HTML index.

        Args:
            config: The index configuration
            python_executor: Python executor instance for running scripts

        Returns:
            List of dictionaries with 'url' and optional 'content' keys
        """
        # Check if using Python override
        if 'python' in config and python_executor:
            context = {'document': self.document} if self.document is not None else {'data': self.json_data}
            result = python_executor.execute(config['python']['script'], context)
            if not isinstance(result, list):
                raise TypeError(f"Index Python script must return list, got {type(result)}")

            # Validate and resolve URLs
            articles = []
            for item in result:
                if not isinstance(item, dict) or 'url' not in item:
                    raise ValueError("Index Python script must return list of dicts with 'url' key")
                article = {'url': resolve_url(self.base_url, item['url'])}
                if 'content' in item:
                    article['content'] = item['content']
                articles.append(article)
            return articles

        # Simple mode
        links_selector = config.get('links')

        if not links_selector:
            raise ValueError("Index: 'links' is required in simple mode")

        articles = []
        try:
            # Select all <a> elements matching the selector
            link_elems = self.document.cssselect(links_selector)
            for link_elem in link_elems:
                href = link_elem.get('href', '')
                if href:
                    articles.append({'url': resolve_url(self.base_url, href)})
        except Exception as e:
            raise Exception(f"Failed to extract index articles: {str(e)}") from e

        return articles

    def transform_url(
        self, url: str, transform_config: dict[str, Any], python_executor=None
    ) -> str:
        """
        Transform a URL using pattern/template or Python script.

        Args:
            url: The URL to transform
            transform_config: The url_transform configuration
            python_executor: Python executor instance for running scripts

        Returns:
            The transformed URL
        """
        # Check if using Python override
        if 'python' in transform_config and python_executor:
            result = python_executor.execute(
                transform_config['python']['script'],
                {'url': url}
            )
            if not isinstance(result, str):
                raise TypeError(f"URL transform Python script must return string, got {type(result)}")
            return result

        # Simple mode: pattern and template
        pattern = transform_config.get('pattern')
        template = transform_config.get('template')

        if not pattern or not template:
            raise ValueError("URL transform requires 'pattern' and 'template' in simple mode")

        # Apply regex pattern
        match = re.search(pattern, url)
        if not match:
            # If pattern doesn't match, return original URL
            return url

        # Replace placeholders in template with captured groups
        # {1}, {2}, etc. are replaced with match groups
        transformed = template
        for i, group in enumerate(match.groups(), start=1):
            transformed = transformed.replace(f'{{{i}}}', group)

        return transformed

    def extract_article_content(
        self, config: dict[str, Any], python_executor=None
    ) -> dict[str, Optional[str]]:
        """
        Extract article content and metadata.

        Args:
            config: The article configuration
            python_executor: Python executor instance for running scripts

        Returns:
            Dictionary with 'content', 'title', 'author', 'date' keys
        """
        result = {
            'content': None,
            'title': None,
            'author': None,
            'date': None
        }

        # Handle JSON response type
        if config.get('response_type') == 'json':
            # Extract HTML (and optionally metadata) from JSON
            if 'json_path' in config:
                json_path = config['json_path']

                if isinstance(json_path, str):
                    # Simple path - extract HTML only
                    html_content = extract_json_path(self.content, json_path)
                    # Resolve relative URLs in the HTML content
                    html_content = resolve_urls_in_html(html_content, self.base_url)
                    # Update document for further processing
                    self.html_content = html_content
                    self.document = html.fromstring(html_content)
                elif isinstance(json_path, dict):
                    # Dict path - extract multiple fields
                    extracted = extract_json_paths(self.content, json_path)

                    # Extract and parse HTML content
                    html_content = extracted['content']

                    # Resolve relative URLs in the HTML content
                    html_content = resolve_urls_in_html(html_content, self.base_url)

                    self.html_content = html_content
                    self.document = html.fromstring(html_content)

                    # Store content directly (no need for CSS selectors)
                    result['content'] = html_content

                    # Extract metadata if provided
                    if 'title' in extracted:
                        result['title'] = extracted['title']
                    if 'author' in extracted:
                        result['author'] = extracted['author']
                    if 'date' in extracted:
                        result['date'] = extracted['date']

                    # If we have content from JSON dict path, we can skip CSS selector processing
                    # But still allow for 'remove' selectors to clean up the HTML
                    if result['content'] and config.get('remove'):
                        # Apply remove selectors to clean up the content
                        remove_selectors = config.get('remove', [])
                        for remove_sel in remove_selectors:
                            for elem in self.document.cssselect(remove_sel):
                                elem.getparent().remove(elem)
                        # Update content after removal
                        result['content'] = etree.tostring(self.document, encoding='unicode', method='html')

                    # Use fallback for missing metadata
                    if not result['title'] or not result['author'] or not result['date']:
                        fallback = extract_metadata_fallback(self.document, self.base_url)
                        if not result['title']:
                            result['title'] = fallback['title']
                        if not result['author']:
                            result['author'] = fallback['author']
                        if not result['date']:
                            result['date'] = fallback['date']

                    return result

        # Check if using Python override
        if 'python' in config and python_executor:
            context = {'document': self.document} if self.document is not None else {'data': self.json_data}
            py_result = python_executor.execute(config['python']['script'], context)

            if isinstance(py_result, str):
                # String return - just content
                result['content'] = py_result
                # Extract metadata using fallback
                fallback = extract_metadata_fallback(self.document, self.base_url)
                result.update(fallback)
            elif isinstance(py_result, dict):
                # Dict return - may include metadata
                if 'content' not in py_result:
                    raise ValueError("Article Python script dict must have 'content' key")
                result['content'] = py_result['content']
                result['title'] = py_result.get('title')
                result['author'] = py_result.get('author')
                result['date'] = py_result.get('date')

                # Use fallback for missing metadata
                if not result['title'] or not result['author'] or not result['date']:
                    fallback = extract_metadata_fallback(self.document, self.base_url)
                    if not result['title']:
                        result['title'] = fallback['title']
                    if not result['author']:
                        result['author'] = fallback['author']
                    if not result['date']:
                        result['date'] = fallback['date']
            else:
                raise TypeError(f"Article Python script must return string or dict, got {type(py_result)}")

            return result

        # Simple mode
        content_selector = config.get('content')
        if not content_selector:
            raise ValueError("Article: 'content' selector is required in simple mode")

        try:
            # Extract content
            content_elem = self.document.cssselect(content_selector)
            if not content_elem or len(content_elem) == 0:
                raise ValueError(f"Content selector '{content_selector}' didn't match any elements")

            content_elem = content_elem[0]

            # Remove unwanted elements
            remove_selectors = config.get('remove', [])
            for remove_sel in remove_selectors:
                for elem in content_elem.cssselect(remove_sel):
                    elem.getparent().remove(elem)

            # Extract HTML content
            html_content = etree.tostring(content_elem, encoding='unicode', method='html')

            # Resolve relative URLs in the HTML content
            html_content = resolve_urls_in_html(html_content, self.base_url)

            result['content'] = html_content

            # Extract metadata using selectors or fallback
            title_selector = config.get('title')
            author_selector = config.get('author')
            date_selector = config.get('date')

            if title_selector:
                title_elem = self.document.cssselect(title_selector)
                if title_elem and len(title_elem) > 0:
                    result['title'] = title_elem[0].text_content().strip()

            if author_selector:
                author_elem = self.document.cssselect(author_selector)
                if author_elem and len(author_elem) > 0:
                    result['author'] = author_elem[0].text_content().strip()

            if date_selector:
                date_elem = self.document.cssselect(date_selector)
                if date_elem and len(date_elem) > 0:
                    # Prefer text content (human-readable) over datetime attribute
                    text = date_elem[0].text_content().strip()
                    result['date'] = text if text else date_elem[0].get('datetime')

            # Use fallback for missing metadata
            if not result['title'] or not result['author'] or not result['date']:
                fallback = extract_metadata_fallback(self.document, self.base_url)
                if not result['title']:
                    result['title'] = fallback['title']
                if not result['author']:
                    result['author'] = fallback['author']
                if not result['date']:
                    result['date'] = fallback['date']

        except Exception as e:
            raise Exception(f"Failed to extract article content: {str(e)}") from e

        return result


def parse_rss_feed(
    feed_url: str, feed_content: str, config: dict[str, Any], python_executor=None
) -> list[dict[str, Any]]:
    """
    Parse an RSS/Atom feed and extract articles.

    Args:
        feed_url: The feed URL (for resolving relative URLs)
        feed_content: The feed XML content
        config: The index configuration
        python_executor: Python executor instance for running scripts

    Returns:
        List of dictionaries with 'url' and optional 'content' keys
    """
    feed = feedparser.parse(feed_content)

    # Check if using Python override
    if 'python' in config and python_executor:
        result = python_executor.execute(config['python']['script'], {'feed': feed})
        if not isinstance(result, list):
            raise TypeError(f"RSS index Python script must return list, got {type(result)}")

        # Validate
        articles = []
        for item in result:
            if not isinstance(item, dict) or 'url' not in item:
                raise ValueError("RSS index Python script must return list of dicts with 'url' key")
            article = {'url': resolve_url(feed_url, item['url'])}
            if 'content' in item:
                article['content'] = item['content']
            articles.append(article)
        return articles

    # Simple mode
    limit = config.get('limit')
    use_content_encoded = config.get('use_content_encoded', False)

    articles = []
    entries = feed.entries[:limit] if limit else feed.entries

    for entry in entries:
        article = {'url': resolve_url(feed_url, entry.link)}

        if use_content_encoded and hasattr(entry, 'content'):
            # Extract content from feed
            if entry.content:
                article['content'] = entry.content[0].value

        articles.append(article)

    return articles
