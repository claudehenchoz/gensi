"""Content extraction from HTML using lxml and CSS selectors."""

from typing import Any, Optional
from lxml import html, etree
import feedparser
from ..utils.url_utils import resolve_url
from ..utils.metadata_fallback import extract_metadata_fallback


class Extractor:
    """Extracts content from HTML using CSS selectors and Python scripts."""

    def __init__(self, base_url: str, html_content: str):
        """
        Initialize the extractor.

        Args:
            base_url: The base URL for resolving relative URLs
            html_content: The HTML content to parse
        """
        self.base_url = base_url
        self.html_content = html_content
        self.document = html.fromstring(html_content)

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
            result = python_executor.execute(config['python']['script'], {'document': self.document})
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
        items_selector = config.get('items')
        link_selector = config.get('link')

        if not items_selector or not link_selector:
            raise ValueError("Index: 'items' and 'link' are required in simple mode")

        articles = []
        try:
            items = self.document.cssselect(items_selector)
            for item in items:
                link_elem = item.cssselect(link_selector)
                if link_elem and len(link_elem) > 0:
                    href = link_elem[0].get('href', '')
                    if href:
                        articles.append({'url': resolve_url(self.base_url, href)})
        except Exception as e:
            raise Exception(f"Failed to extract index articles: {str(e)}") from e

        return articles

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

        # Check if using Python override
        if 'python' in config and python_executor:
            py_result = python_executor.execute(config['python']['script'], {'document': self.document})

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

            result['content'] = etree.tostring(content_elem, encoding='unicode', method='html')

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
                    # Try to get datetime attribute first, then text
                    result['date'] = date_elem[0].get('datetime') or date_elem[0].text_content().strip()

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
        article = {'url': entry.link}

        if use_content_encoded and hasattr(entry, 'content'):
            # Extract content from feed
            if entry.content:
                article['content'] = entry.content[0].value

        articles.append(article)

    return articles
