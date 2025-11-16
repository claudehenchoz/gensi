"""Image processing for articles - download and embed images in EPUB."""

import hashlib
from pathlib import Path
from typing import Optional
from lxml import html, etree
from urllib.parse import urlparse

from ..utils.url_utils import resolve_url


class ImageProcessor:
    """Processes images in article content."""

    # Common lazy-loading attributes
    LAZY_LOAD_ATTRS = ['data-src', 'data-lazy-src', 'data-original', 'data-lazy', 'data-srcset']

    def __init__(self):
        """Initialize the image processor."""
        self.images = {}  # Map of original URL -> (local_path, image_data)

    def extract_images(self, html_content: str, base_url: str) -> list[dict]:
        """
        Extract all image URLs from HTML content.

        Args:
            html_content: The HTML content to process
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dicts with 'url' and 'element_info' for each image
        """
        images = []
        try:
            doc = html.fromstring(html_content)

            for img in doc.xpath('//img'):
                img_url = None

                # Try standard src first
                if img.get('src'):
                    img_url = img.get('src')

                # Check for lazy-loading attributes
                if not img_url or img_url.startswith('data:'):
                    for attr in self.LAZY_LOAD_ATTRS:
                        if img.get(attr):
                            img_url = img.get(attr)
                            break

                # Skip if no valid URL found
                if not img_url or img_url.startswith('data:'):
                    continue

                # Resolve to absolute URL
                absolute_url = resolve_url(base_url, img_url)

                images.append({
                    'url': absolute_url,
                    'original_url': img_url
                })

        except Exception as e:
            # If parsing fails, return empty list
            pass

        return images

    def normalize_lazy_loaded_images(self, html_content: str) -> str:
        """
        Normalize lazy-loaded images by moving data-src to src.

        Args:
            html_content: The HTML content to process

        Returns:
            HTML content with normalized img tags
        """
        try:
            doc = html.fromstring(html_content)

            for img in doc.xpath('//img'):
                # Check for lazy-loading attributes
                for attr in self.LAZY_LOAD_ATTRS:
                    if img.get(attr):
                        lazy_src = img.get(attr)
                        # Only replace if current src is placeholder or missing
                        current_src = img.get('src', '')
                        if not current_src or current_src.startswith('data:') or \
                           'placeholder' in current_src.lower() or 'loading' in current_src.lower():
                            img.set('src', lazy_src)
                        # Remove the lazy-loading attribute
                        del img.attrib[attr]

            return etree.tostring(doc, encoding='unicode', method='html')
        except Exception:
            return html_content

    def get_image_filename(self, url: str, index: int) -> str:
        """
        Generate a unique filename for an image.

        Args:
            url: The image URL
            index: Image index for uniqueness

        Returns:
            A filename like "image_001_abc123.jpg"
        """
        # Get file extension from URL
        parsed = urlparse(url)
        path = parsed.path
        ext = Path(path).suffix.lower()

        # Default to .jpg if no extension
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']:
            ext = '.jpg'

        # Create hash of URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        return f"image_{index:03d}_{url_hash}{ext}"

    def remove_images(self, html_content: str) -> str:
        """
        Remove all img tags from HTML content.

        Args:
            html_content: The HTML content to process

        Returns:
            HTML content with img tags removed
        """
        try:
            doc = html.fromstring(html_content)

            # Find and remove all img elements
            for img in doc.xpath('//img'):
                parent = img.getparent()
                if parent is not None:
                    # Preserve tail text (text after the img tag)
                    if img.tail:
                        prev = img.getprevious()
                        if prev is not None:
                            prev.tail = (prev.tail or '') + img.tail
                        else:
                            parent.text = (parent.text or '') + img.tail
                    parent.remove(img)

            return etree.tostring(doc, encoding='unicode', method='html')
        except Exception:
            return html_content

    def update_image_references(self, html_content: str, base_url: str, image_map: dict[str, str]) -> str:
        """
        Update image src attributes to reference embedded images.

        Args:
            html_content: The HTML content to process
            base_url: Base URL for resolving relative URLs
            image_map: Mapping of absolute URL -> EPUB path

        Returns:
            HTML content with updated img tags
        """
        try:
            doc = html.fromstring(html_content)

            for img in doc.xpath('//img'):
                # Get the current src
                current_src = img.get('src', '')
                if current_src:
                    absolute_url = resolve_url(base_url, current_src)

                    # If we have this image in our map, update the reference
                    if absolute_url in image_map:
                        img.set('src', f"../{image_map[absolute_url]}")

            return etree.tostring(doc, encoding='unicode', method='html')
        except Exception:
            return html_content

    async def download_images(self, images: list[dict], fetcher) -> dict[str, tuple[str, bytes]]:
        """
        Download images in parallel.

        Args:
            images: List of image dicts with 'url'
            fetcher: Fetcher instance for downloading

        Returns:
            Dict mapping absolute URL -> (filename, image_data)
        """
        image_map = {}

        for i, img_info in enumerate(images):
            url = img_info['url']

            # Skip if already downloaded
            if url in image_map:
                continue

            try:
                # Download image
                image_data, _ = await fetcher.fetch_binary(url)

                # Generate filename
                filename = self.get_image_filename(url, i)

                image_map[url] = (filename, image_data)
            except Exception as e:
                # Skip failed downloads
                pass

        return image_map


async def process_article_images(
    html_content: str,
    base_url: str,
    fetcher,
    enable_images: bool = True
) -> tuple[str, dict[str, tuple[str, bytes]]]:
    """
    Process images in article content.

    Args:
        html_content: The HTML content to process
        base_url: Base URL for the article
        fetcher: Fetcher instance for downloading
        enable_images: Whether to download images (default: True).
                      If False, all img tags will be removed.

    Returns:
        Tuple of (updated_html_content, image_map)
        where image_map is {absolute_url: (filename, image_data)}
    """
    processor = ImageProcessor()

    # If images are disabled, remove all img tags and return empty map
    if not enable_images:
        html_content = processor.remove_images(html_content)
        return html_content, {}

    # First, normalize lazy-loaded images
    html_content = processor.normalize_lazy_loaded_images(html_content)

    # Extract all images
    images = processor.extract_images(html_content, base_url)

    # Download images
    image_map = await processor.download_images(images, fetcher)

    # Update image references in HTML
    epub_path_map = {url: f"images/{filename}" for url, (filename, _) in image_map.items()}
    html_content = processor.update_image_references(html_content, base_url, epub_path_map)

    return html_content, image_map
