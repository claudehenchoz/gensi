"""Metadata extraction fallback logic for HTML pages."""

from typing import Optional
from lxml import html


def extract_metadata_fallback(document: html.HtmlElement, url: str) -> dict[str, Optional[str]]:
    """
    Extract metadata from HTML using fallback logic.

    Tries to extract title, author, and date from common HTML meta tags
    when CSS selectors don't match or aren't provided.

    Args:
        document: The parsed HTML document
        url: The source URL (for context)

    Returns:
        Dictionary with 'title', 'author', and 'date' keys (values may be None)
    """
    metadata = {
        'title': None,
        'author': None,
        'date': None
    }

    # Title fallback
    title_selectors = [
        '//meta[@property="og:title"]/@content',
        '//meta[@name="twitter:title"]/@content',
        '//title/text()',
        '//h1/text()',
    ]
    for selector in title_selectors:
        try:
            result = document.xpath(selector)
            if result and result[0].strip():
                metadata['title'] = result[0].strip()
                break
        except Exception:
            continue

    # Author fallback
    author_selectors = [
        '//meta[@name="author"]/@content',
        '//meta[@property="article:author"]/@content',
        '//meta[@property="og:article:author"]/@content',
        '//span[@class="author"]/text()',
        '//div[@class="author"]/text()',
        '//a[@rel="author"]/text()',
    ]
    for selector in author_selectors:
        try:
            result = document.xpath(selector)
            if result and result[0].strip():
                metadata['author'] = result[0].strip()
                break
        except Exception:
            continue

    # Date fallback
    date_selectors = [
        '//meta[@property="article:published_time"]/@content',
        '//meta[@property="og:article:published_time"]/@content',
        '//time/@datetime',
        '//meta[@name="date"]/@content',
        '//meta[@name="pubdate"]/@content',
        '//time/text()',
    ]
    for selector in date_selectors:
        try:
            result = document.xpath(selector)
            if result and result[0].strip():
                metadata['date'] = result[0].strip()
                break
        except Exception:
            continue

    return metadata
