"""Thumbnail extraction from HTML for automatic cover generation."""

import json
import logging
from typing import List, Optional
from lxml import html
from urllib.parse import urlparse, parse_qs
from .url_utils import resolve_url

logger = logging.getLogger(__name__)


class ThumbnailCandidate:
    """Represents a thumbnail candidate with scoring."""

    def __init__(self, url: str, source: str, score: float = 0.0):
        self.url = url
        self.source = source  # 'meta', 'jsonld', 'body'
        self.score = score

    def __repr__(self):
        return f"<ThumbnailCandidate url={self.url[:50]}... source={self.source} score={self.score}>"


def extract_thumbnails(document: html.HtmlElement, base_url: str, max_count: int = 6) -> List[str]:
    """
    Extract thumbnail candidates from HTML document.

    Extracts thumbnails from multiple sources (meta tags, JSON-LD, body images),
    scores them by quality/relevance, deduplicates, and returns the top candidates.

    Args:
        document: The parsed HTML document (lxml element)
        base_url: Base URL for resolving relative URLs
        max_count: Maximum number of thumbnails to return (default: 6)

    Returns:
        List of absolute image URLs, ordered by relevance (max_count items)
    """
    try:
        candidates = []

        # Extract from all sources
        candidates.extend(_extract_from_meta_tags(document))
        candidates.extend(_extract_from_jsonld(document))
        candidates.extend(_extract_from_body(document, base_url))

        # Deduplicate
        candidates = _deduplicate_thumbnails(candidates)

        # Sort by score (descending)
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Resolve to absolute URLs and take top max_count
        result = []
        for candidate in candidates[:max_count]:
            absolute_url = resolve_url(base_url, candidate.url)
            if absolute_url:
                result.append(absolute_url)
                logger.debug(f"Thumbnail: {absolute_url} (source={candidate.source}, score={candidate.score})")

        return result

    except Exception as e:
        logger.debug(f"Failed to extract thumbnails: {e}")
        return []


def _extract_from_meta_tags(document: html.HtmlElement) -> List[ThumbnailCandidate]:
    """Extract thumbnails from Open Graph and Twitter Card meta tags."""
    candidates = []

    # Meta tag selectors (property and name variants)
    selectors = [
        '//meta[@property="og:image"]/@content',
        '//meta[@property="og:image:url"]/@content',
        '//meta[@name="twitter:image"]/@content',
        '//meta[@name="twitter:image:src"]/@content',
        '//meta[@property="article:image"]/@content',
        '//link[@rel="image_src"]/@href',
    ]

    seen_urls = set()
    for selector in selectors:
        try:
            results = document.xpath(selector)
            for url in results:
                url = url.strip()
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    candidates.append(ThumbnailCandidate(url, 'meta', score=10.0))
        except Exception as e:
            logger.debug(f"Meta tag extraction failed for {selector}: {e}")
            continue

    return candidates


def _extract_from_jsonld(document: html.HtmlElement) -> List[ThumbnailCandidate]:
    """Extract thumbnails from JSON-LD structured data (schema.org)."""
    candidates = []

    try:
        # Find all JSON-LD script tags
        scripts = document.xpath('//script[@type="application/ld+json"]/text()')

        for script_text in scripts:
            try:
                data = json.loads(script_text)

                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # Check if it's an Article type
                    item_type = item.get('@type', '')
                    if not isinstance(item_type, str):
                        item_type = str(item_type) if item_type else ''

                    if 'Article' in item_type or 'Posting' in item_type:
                        # Extract image URLs from various fields
                        image_fields = ['image', 'thumbnailUrl', 'primaryImageOfPage']

                        for field in image_fields:
                            image_data = item.get(field)
                            if not image_data:
                                continue

                            # Handle different formats
                            urls = []
                            if isinstance(image_data, str):
                                urls = [image_data]
                            elif isinstance(image_data, list):
                                urls = [u for u in image_data if isinstance(u, str)]
                            elif isinstance(image_data, dict):
                                # Could be ImageObject with 'url' field
                                if 'url' in image_data:
                                    url_val = image_data['url']
                                    if isinstance(url_val, str):
                                        urls = [url_val]

                            for url in urls:
                                url = url.strip()
                                if url:
                                    candidates.append(ThumbnailCandidate(url, 'jsonld', score=9.0))

            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")
                continue
            except Exception as e:
                logger.debug(f"Failed to extract from JSON-LD: {e}")
                continue

    except Exception as e:
        logger.debug(f"JSON-LD extraction failed: {e}")

    return candidates


def _extract_from_body(document: html.HtmlElement, base_url: str) -> List[ThumbnailCandidate]:
    """Extract thumbnails from <img> tags in the document body with quality scoring."""
    candidates = []

    try:
        images = document.xpath('//img')

        for img in images:
            try:
                score = _score_image(img, base_url)

                # Skip images with negative scores (icons, ads, etc.)
                if score < 0:
                    continue

                # Get image URL (handle lazy-loading attributes)
                url = (img.get('src') or
                       img.get('data-src') or
                       img.get('data-lazy-src') or
                       img.get('data-original') or
                       img.get('data-lazy'))

                if url and url.strip():
                    candidates.append(ThumbnailCandidate(url.strip(), 'body', score=score))

            except Exception as e:
                logger.debug(f"Failed to score image: {e}")
                continue

    except Exception as e:
        logger.debug(f"Body image extraction failed: {e}")

    return candidates


def _score_image(img_elem: html.HtmlElement, base_url: str) -> float:
    """
    Score an image based on quality indicators.

    Scoring factors:
    - Dimensions (width/height)
    - Context (parent tags, classes)
    - Image URL patterns

    Returns a score (can be negative to filter out)
    """
    score = 5.0  # Base score for body images

    # Get attributes
    src = img_elem.get('src', '') or img_elem.get('data-src', '')
    width = img_elem.get('width', '')
    height = img_elem.get('height', '')
    img_class = (img_elem.get('class', '') or '').lower()
    alt = img_elem.get('alt', '')

    # Parse dimensions
    try:
        width_val = int(width) if width.isdigit() else 0
        height_val = int(height) if height.isdigit() else 0
    except (ValueError, AttributeError):
        width_val = 0
        height_val = 0

    # Dimension boosters
    if width_val >= 400:
        score += 3.0
    if height_val >= 300:
        score += 3.0
    if width_val > 0 and height_val > 0:
        score += 1.0  # Has explicit dimensions

    # Dimension penalties
    if width_val > 0 and width_val < 200:
        score -= 5.0
    if height_val > 0 and height_val < 200:
        score -= 5.0

    # Context boosters (parent elements)
    parent = img_elem.getparent()
    if parent is not None:
        parent_tag = parent.tag.lower() if hasattr(parent, 'tag') else ''
        if parent_tag == 'figure':
            score += 2.0
        elif parent_tag == 'article':
            score += 1.0

    # Class boosters
    if any(keyword in img_class for keyword in ['featured', 'hero', 'main', 'thumbnail']):
        score += 2.0

    # Alt text booster
    if alt and len(alt) > 10:
        score += 0.5

    # Class penalties (icons, logos, ads) - very strong penalties to override dimension boosters
    if any(keyword in img_class for keyword in ['icon', 'avatar', 'logo', 'badge', 'emoji']):
        score -= 20.0  # Strong penalty to ensure negative score
    if any(keyword in img_class for keyword in ['ad', 'banner', 'sponsor']):
        score -= 20.0  # Strong penalty to ensure negative score

    # URL penalties (tracking pixels, ads)
    src_lower = src.lower()
    if src.startswith('data:'):
        score -= 20.0  # Base64 embedded images - strong penalty
    if any(keyword in src_lower for keyword in ['tracking', 'pixel', 'ad', '1x1']):
        score -= 20.0  # Strong penalty to ensure negative score

    return score


def _deduplicate_thumbnails(candidates: List[ThumbnailCandidate]) -> List[ThumbnailCandidate]:
    """
    Remove duplicate URLs, keeping the highest-scored version.

    Normalizes URLs by removing query parameters for comparison,
    but keeps the original URL with parameters.
    """
    # Group by normalized URL
    url_groups = {}

    for candidate in candidates:
        # Normalize URL for comparison (remove query params)
        normalized = _normalize_url_for_comparison(candidate.url)

        if normalized not in url_groups:
            url_groups[normalized] = candidate
        else:
            # Keep the one with higher score
            if candidate.score > url_groups[normalized].score:
                url_groups[normalized] = candidate

    return list(url_groups.values())


def _normalize_url_for_comparison(url: str) -> str:
    """Normalize URL for deduplication comparison (remove query params)."""
    try:
        parsed = urlparse(url)
        # Reconstruct without query and fragment
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        # If parsing fails, return original
        return url
