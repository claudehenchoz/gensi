"""Tests for the image optimizer module."""

import io
from PIL import Image
import pytest

from gensi.core.image_optimizer import (
    detect_image_format,
    has_transparency,
    resize_image,
    normalize_image_format,
    optimize_image,
    process_image,
    COVER_MAX_WIDTH,
    COVER_MAX_HEIGHT,
    ARTICLE_MAX_WIDTH,
    ARTICLE_MAX_HEIGHT,
)


class TestImageFormatDetection:
    """Test format detection functionality."""

    def test_detect_jpeg_format(self):
        """Test detecting JPEG format."""
        # Create a simple JPEG image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        image_data = buffer.getvalue()

        format_type = detect_image_format(image_data)
        assert format_type == 'JPEG'

    def test_detect_png_format(self):
        """Test detecting PNG format."""
        # Create a simple PNG image
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_data = buffer.getvalue()

        format_type = detect_image_format(image_data)
        assert format_type == 'PNG'

    def test_detect_webp_format(self):
        """Test detecting WebP format."""
        # Create a simple WebP image
        img = Image.new('RGB', (100, 100), color='green')
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP')
        image_data = buffer.getvalue()

        format_type = detect_image_format(image_data)
        assert format_type == 'WEBP'


class TestTransparencyDetection:
    """Test transparency detection."""

    def test_has_transparency_rgba(self):
        """Test detecting transparency in RGBA image."""
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        assert has_transparency(img) is True

    def test_has_transparency_rgb(self):
        """Test RGB image has no transparency."""
        img = Image.new('RGB', (100, 100), color='red')
        assert has_transparency(img) is False

    def test_has_transparency_la(self):
        """Test detecting transparency in LA (grayscale with alpha) image."""
        img = Image.new('LA', (100, 100))
        assert has_transparency(img) is True

    def test_has_transparency_palette_with_transparency(self):
        """Test detecting transparency in palette mode."""
        img = Image.new('P', (100, 100))
        img.info['transparency'] = 0
        assert has_transparency(img) is True


class TestImageResizing:
    """Test image resizing functionality."""

    def test_resize_oversized_cover_image(self):
        """Test resizing an oversized cover image."""
        # Create an image larger than cover max dimensions
        img = Image.new('RGB', (2000, 3000), color='red')
        resized = resize_image(img, COVER_MAX_WIDTH, COVER_MAX_HEIGHT)

        # Should be resized to fit within cover dimensions
        assert resized.size[0] <= COVER_MAX_WIDTH
        assert resized.size[1] <= COVER_MAX_HEIGHT

        # Aspect ratio should be preserved
        original_ratio = img.size[0] / img.size[1]
        resized_ratio = resized.size[0] / resized.size[1]
        assert abs(original_ratio - resized_ratio) < 0.01

    def test_resize_oversized_article_image(self):
        """Test resizing an oversized article image."""
        # Create an image larger than article max dimensions
        img = Image.new('RGB', (1500, 2000), color='blue')
        resized = resize_image(img, ARTICLE_MAX_WIDTH, ARTICLE_MAX_HEIGHT)

        # Should be resized to fit within article dimensions
        assert resized.size[0] <= ARTICLE_MAX_WIDTH
        assert resized.size[1] <= ARTICLE_MAX_HEIGHT

    def test_resize_small_image_not_resized(self):
        """Test that small images are not resized."""
        img = Image.new('RGB', (500, 500), color='green')
        resized = resize_image(img, COVER_MAX_WIDTH, COVER_MAX_HEIGHT)

        # Should remain the same size
        assert resized.size == (500, 500)

    def test_resize_preserves_aspect_ratio_width_constrained(self):
        """Test aspect ratio preservation when width is the constraint."""
        # Wide image: 2000x1000 (2:1 ratio)
        img = Image.new('RGB', (2000, 1000), color='yellow')
        resized = resize_image(img, COVER_MAX_WIDTH, COVER_MAX_HEIGHT)

        # Width should be at max, height scaled proportionally
        assert resized.size[0] == COVER_MAX_WIDTH
        expected_height = int(1000 * (COVER_MAX_WIDTH / 2000))
        assert resized.size[1] == expected_height

    def test_resize_preserves_aspect_ratio_height_constrained(self):
        """Test aspect ratio preservation when height is the constraint."""
        # Tall image: 1000x2000 (1:2 ratio)
        img = Image.new('RGB', (1000, 2000), color='purple')
        resized = resize_image(img, COVER_MAX_WIDTH, COVER_MAX_HEIGHT)

        # Height should be at max, width scaled proportionally
        assert resized.size[1] == COVER_MAX_HEIGHT
        expected_width = int(1000 * (COVER_MAX_HEIGHT / 2000))
        assert resized.size[0] == expected_width


class TestFormatNormalization:
    """Test format normalization (webp/others to jpg/png)."""

    def test_normalize_opaque_image_to_jpeg(self):
        """Test that opaque images are converted to JPEG."""
        img = Image.new('RGB', (100, 100), color='red')
        target_format, extension = normalize_image_format(img, 'WEBP')

        assert target_format == 'JPEG'
        assert extension == 'jpg'

    def test_normalize_transparent_image_to_png(self):
        """Test that transparent images are converted to PNG."""
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        target_format, extension = normalize_image_format(img, 'WEBP')

        assert target_format == 'PNG'
        assert extension == 'png'


class TestImageOptimization:
    """Test image optimization and compression."""

    def test_optimize_jpeg_produces_smaller_file(self):
        """Test that JPEG optimization reduces file size."""
        # Create a large uncompressed image
        img = Image.new('RGB', (1000, 1000), color='red')

        # Save unoptimized at 100% quality
        unoptimized = io.BytesIO()
        img.save(unoptimized, format='JPEG', quality=100)
        unoptimized_size = len(unoptimized.getvalue())

        # Optimize at 80% quality
        optimized_data = optimize_image(img, 'JPEG')
        optimized_size = len(optimized_data)

        # Optimized should be smaller
        assert optimized_size < unoptimized_size

    def test_optimize_png_preserves_transparency(self):
        """Test that PNG optimization preserves transparency."""
        # Create a transparent PNG
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        optimized_data = optimize_image(img, 'PNG')

        # Re-open and verify it still has alpha channel
        optimized_img = Image.open(io.BytesIO(optimized_data))
        assert optimized_img.mode == 'RGBA'

    def test_optimize_converts_rgba_to_rgb_for_jpeg(self):
        """Test that RGBA images are converted to RGB for JPEG."""
        # Create an RGBA image
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
        optimized_data = optimize_image(img, 'JPEG')

        # Re-open and verify it's RGB
        optimized_img = Image.open(io.BytesIO(optimized_data))
        assert optimized_img.mode == 'RGB'


class TestProcessImage:
    """Test the complete image processing pipeline."""

    def test_process_oversized_jpeg_cover(self):
        """Test processing an oversized JPEG as a cover image."""
        # Create a large JPEG
        img = Image.new('RGB', (2000, 3000), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=100)
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/cover.jpg', image_type='cover'
        )

        # Verify extension
        assert extension == 'jpg'

        # Verify it's resized
        processed_img = Image.open(io.BytesIO(processed_data))
        assert processed_img.size[0] <= COVER_MAX_WIDTH
        assert processed_img.size[1] <= COVER_MAX_HEIGHT

        # Verify it's smaller
        assert len(processed_data) < len(image_data)

    def test_process_oversized_jpeg_article(self):
        """Test processing an oversized JPEG as an article image."""
        # Create a large JPEG
        img = Image.new('RGB', (1500, 2000), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=100)
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/article.jpg', image_type='article'
        )

        # Verify extension
        assert extension == 'jpg'

        # Verify it's resized to article dimensions
        processed_img = Image.open(io.BytesIO(processed_data))
        assert processed_img.size[0] <= ARTICLE_MAX_WIDTH
        assert processed_img.size[1] <= ARTICLE_MAX_HEIGHT

    def test_process_webp_without_transparency_converts_to_jpeg(self):
        """Test that WebP without transparency is converted to JPEG."""
        # Create a WebP without transparency
        img = Image.new('RGB', (800, 600), color='green')
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP')
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/image.webp', image_type='article'
        )

        # Should be converted to JPEG
        assert extension == 'jpg'

        # Verify format
        processed_img = Image.open(io.BytesIO(processed_data))
        assert processed_img.format == 'JPEG'

    def test_process_webp_with_transparency_converts_to_png(self):
        """Test that WebP with transparency is converted to PNG."""
        # Create a WebP with transparency
        img = Image.new('RGBA', (800, 600), color=(0, 255, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP')
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/image.webp', image_type='article'
        )

        # Should be converted to PNG
        assert extension == 'png'

        # Verify format and transparency preserved
        processed_img = Image.open(io.BytesIO(processed_data))
        assert processed_img.format == 'PNG'
        assert processed_img.mode == 'RGBA'

    def test_process_png_preserves_format(self):
        """Test that PNG images remain PNG."""
        # Create a PNG
        img = Image.new('RGBA', (500, 500), color=(255, 0, 0, 200))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/image.png', image_type='article'
        )

        # Should remain PNG
        assert extension == 'png'

    def test_process_invalid_image_raises_error(self):
        """Test that invalid image data raises an error."""
        invalid_data = b'not an image'

        with pytest.raises(ValueError):
            process_image(invalid_data, 'http://example.com/invalid.jpg', image_type='article')

    def test_process_small_image_not_resized(self):
        """Test that images smaller than max dimensions are not resized."""
        # Create a small image
        img = Image.new('RGB', (400, 400), color='yellow')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=100)
        image_data = buffer.getvalue()

        processed_data, extension = process_image(
            image_data, 'http://example.com/small.jpg', image_type='article'
        )

        # Verify it's not resized (but still optimized)
        processed_img = Image.open(io.BytesIO(processed_data))
        assert processed_img.size == (400, 400)

        # Should still be smaller due to compression
        assert len(processed_data) < len(image_data)
