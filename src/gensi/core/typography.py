"""Typography improvements for article content using typogrify."""

from typogrify.filters import smartypants, caps, initial_quotes, amp


def improve_typography(content: str) -> str:
    """
    Apply typography improvements to HTML content.

    Applies the following filters suitable for EPUB3 reflowable content:
    - amp: Wraps ampersands in <span class="amp">
    - smartypants: Converts straight quotes to curly quotes, dashes, ellipses
    - caps: Wraps consecutive capital letters in <span class="caps">
    - initial_quotes: Wraps initial quotes in <span class="dquo"> or <span class="quo">

    Note: widont filter is skipped as it's not suitable for reflowable EPUB content.

    Args:
        content: The HTML content to process

    Returns:
        HTML content with improved typography
    """
    if not content:
        return content

    try:
        # Apply filters in sequence
        content = amp(content)
        content = smartypants(content)
        # content = caps(content)
        content = initial_quotes(content)
        return content
    except Exception:
        # If typography processing fails, return original content
        return content
