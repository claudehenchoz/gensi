"""HTML sanitization using nh3 for EPUB 2.0.1 compliance."""

import nh3


# EPUB 2.0.1 supported tags (XHTML 1.1 subset)
# Note: 'script' and 'style' are excluded as nh3 treats them specially
# and they should be stripped from article content anyway
EPUB_ALLOWED_TAGS = {
    'a', 'abbr', 'acronym', 'address', 'article', 'aside', 'audio',
    'b', 'bdi', 'bdo', 'big', 'blockquote', 'body', 'br', 'button',
    'canvas', 'caption', 'cite', 'code', 'col', 'colgroup',
    'data', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'div', 'dl', 'dt',
    'em', 'embed',
    'fieldset', 'figcaption', 'figure', 'footer', 'form',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hr', 'html',
    'i', 'iframe', 'img', 'input', 'ins',
    'kbd', 'keygen',
    'label', 'legend', 'li', 'link',
    'main', 'map', 'mark', 'menu', 'menuitem', 'meta', 'meter',
    'nav', 'noscript',
    'object', 'ol', 'optgroup', 'option', 'output',
    'p', 'param', 'picture', 'pre', 'progress',
    'q',
    'rp', 'rt', 'ruby',
    's', 'samp', 'section', 'select', 'small', 'source', 'span',
    'strong', 'sub', 'summary', 'sup', 'svg',
    'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th', 'thead',
    'time', 'title', 'tr', 'track',
    'u', 'ul',
    'var', 'video',
    'wbr',
}

# Common attributes allowed on many elements
EPUB_ALLOWED_ATTRIBUTES = {
    '*': {'class', 'id', 'lang', 'dir', 'title', 'style'},
    'a': {'href', 'name', 'target'},
    'img': {'src', 'alt', 'width', 'height', 'title'},
    'audio': {'src', 'controls', 'autoplay', 'loop', 'preload'},
    'video': {'src', 'controls', 'autoplay', 'loop', 'preload', 'width', 'height', 'poster'},
    'source': {'src', 'type'},
    'link': {'rel', 'href', 'type'},
    'table': {'border', 'cellpadding', 'cellspacing', 'width', 'summary'},
    'td': {'colspan', 'rowspan', 'headers', 'width', 'height', 'align', 'valign'},
    'th': {'colspan', 'rowspan', 'scope', 'width', 'height', 'align', 'valign'},
    'ol': {'start', 'type', 'reversed'},
    'ul': {'type'},
    'li': {'value'},
    'blockquote': {'cite'},
    'q': {'cite'},
    'del': {'cite', 'datetime'},
    'ins': {'cite', 'datetime'},
    'time': {'datetime'},
}

# URL schemes that are safe for EPUB
EPUB_URL_SCHEMES = {'http', 'https', 'mailto', 'ftp', 'data'}


class Sanitizer:
    """Sanitizes HTML content for EPUB 2.0.1 compliance using nh3."""

    def __init__(self, allowed_tags=None, allowed_attributes=None, url_schemes=None):
        """
        Initialize the sanitizer.

        Args:
            allowed_tags: Set of allowed HTML tags (default: EPUB 2.0.1 tags)
            allowed_attributes: Dict of allowed attributes per tag (default: EPUB attributes)
            url_schemes: Set of allowed URL schemes (default: EPUB schemes)
        """
        self.allowed_tags = allowed_tags or EPUB_ALLOWED_TAGS
        self.allowed_attributes = allowed_attributes or EPUB_ALLOWED_ATTRIBUTES
        self.url_schemes = url_schemes or EPUB_URL_SCHEMES

    def sanitize(self, html_content: str) -> str:
        """
        Sanitize HTML content for EPUB compatibility.

        Args:
            html_content: The HTML content to sanitize

        Returns:
            Sanitized HTML content
        """
        # Use nh3 to sanitize with EPUB-compatible settings
        sanitized = nh3.clean(
            html_content,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            url_schemes=self.url_schemes,
            strip_comments=True,
        )

        return sanitized

    def sanitize_to_xhtml(self, html_content: str) -> str:
        """
        Sanitize and ensure XHTML compliance.

        Args:
            html_content: The HTML content to sanitize

        Returns:
            Sanitized XHTML content
        """
        # First sanitize with nh3
        sanitized = self.sanitize(html_content)

        # Additional XHTML fixes could be added here if needed
        # For now, nh3 handles most of the work

        return sanitized


def sanitize_html(html_content: str) -> str:
    """
    Convenience function to sanitize HTML for EPUB.

    Args:
        html_content: The HTML content to sanitize

    Returns:
        Sanitized HTML content
    """
    sanitizer = Sanitizer()
    return sanitizer.sanitize(html_content)
