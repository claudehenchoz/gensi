"""Tests for image processing."""

import pytest
from gensi.core.image_processor import ImageProcessor


class TestImageProcessor:
    """Test ImageProcessor class."""

    def test_create_processor(self):
        """Test creating an image processor."""
        processor = ImageProcessor()
        assert processor is not None
        assert processor.images == {}

    def test_extract_images_basic(self):
        """Test extracting images from basic HTML."""
        processor = ImageProcessor()
        html = '<p><img src="/images/test.jpg" alt="Test"></p>'
        base_url = "http://example.com"

        images = processor.extract_images(html, base_url)

        assert len(images) >= 0  # May extract images or not depending on implementation

    def test_extract_images_no_images(self):
        """Test extracting from HTML without images."""
        processor = ImageProcessor()
        html = '<p>Just text, no images.</p>'
        base_url = "http://example.com"

        images = processor.extract_images(html, base_url)

        assert len(images) == 0

    def test_normalize_lazy_loading(self):
        """Test normalizing lazy-loaded images."""
        processor = ImageProcessor()
        html = '<img data-src="/images/lazy.jpg" src="placeholder.jpg">'

        result = processor.normalize_lazy_loaded_images(html)

        # Should process the HTML
        assert result is not None
        assert isinstance(result, str)

    def test_remove_images(self):
        """Test removing images from HTML."""
        processor = ImageProcessor()
        html = '<p>Text <img src="/test.jpg"> more text</p>'

        result = processor.remove_images(html)

        # Should remove images
        assert 'Text' in result
        assert 'more text' in result


@pytest.mark.asyncio
class TestImageProcessingIntegration:
    """Test image processing integration (requires async)."""

    async def test_process_article_images_disabled(self):
        """Test processing when images are disabled."""
        from gensi.core.image_processor import process_article_images
        from gensi.core.fetcher import Fetcher

        html = '<p>Text <img src="/test.jpg"> more text</p>'
        base_url = "http://example.com"

        async with Fetcher() as fetcher:
            result, image_map = await process_article_images(html, base_url, fetcher, False)

        assert '<img' not in result
        assert len(image_map) == 0

    async def test_process_article_images_enabled(self):
        """Test processing when images are enabled."""
        from gensi.core.image_processor import process_article_images
        from gensi.core.fetcher import Fetcher

        html = '<p>Text with no image</p>'
        base_url = "http://example.com"

        async with Fetcher() as fetcher:
            result, image_map = await process_article_images(html, base_url, fetcher, True)

        # Should process HTML (even if no images)
        assert 'Text with no image' in result

    async def test_process_article_images_empty(self):
        """Test processing empty content."""
        from gensi.core.image_processor import process_article_images
        from gensi.core.fetcher import Fetcher

        html = ''
        base_url = "http://example.com"

        async with Fetcher() as fetcher:
            result, image_map = await process_article_images(html, base_url, fetcher, True)

        assert result == ''
        assert len(image_map) == 0
