"""URL utilities for resolving and validating URLs."""

from urllib.parse import urljoin, urlparse


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
