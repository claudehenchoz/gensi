"""URL utilities for resolving and validating URLs."""

from urllib.parse import urljoin, urlparse
from lxml import html as lxml_html, etree


def resolve_url(base_url: str, url: str) -> str:
    """
    Resolve a URL relative to a base URL.

    Args:
        base_url: The base URL to resolve against
        url: The URL to resolve (can be relative or absolute)

    Returns:
        The absolute URL
    """
    return urljoin(base_url, url)


def is_image_url(url: str) -> bool:
    """
    Check if a URL points to an image file based on extension.

    Args:
        url: The URL to check

    Returns:
        True if the URL appears to be an image file
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
    return any(path.endswith(ext) for ext in image_extensions)


def get_base_url(url: str) -> str:
    """
    Extract the base URL (scheme + netloc) from a URL.

    Args:
        url: The URL to extract base from

    Returns:
        The base URL (e.g., "https://example.com")
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def resolve_urls_in_html(html_content: str, base_url: str) -> str:
    """
    Resolve all relative URLs in HTML content to absolute URLs.

    This processes all href and src attributes in the HTML and converts
    relative URLs to absolute URLs based on the provided base URL.

    Args:
        html_content: The HTML content to process
        base_url: The base URL to resolve relative URLs against

    Returns:
        HTML content with all URLs resolved to absolute URLs
    """
    try:
        # Parse HTML
        doc = lxml_html.fromstring(html_content)

        # Resolve all href attributes
        for elem in doc.xpath('.//*[@href]'):
            href = elem.get('href')
            if href:
                elem.set('href', resolve_url(base_url, href))

        # Resolve all src attributes
        for elem in doc.xpath('.//*[@src]'):
            src = elem.get('src')
            if src:
                elem.set('src', resolve_url(base_url, src))

        # Convert back to string
        return etree.tostring(doc, encoding='unicode', method='html')
    except Exception:
        # If parsing fails, return original content
        return html_content
