"""Tests for automatic cover generation."""

import pytest
import io
from PIL import Image
from unittest.mock import AsyncMock, MagicMock, patch
from gensi.core.cover_generator import CoverGenerator, COVER_WIDTH, COVER_HEIGHT, BANNER_HEIGHT


class TestTextCoverGeneration:
    """Test text-only cover generation."""

    def test_generate_text_cover_basic(self):
        """Test generation of basic text cover."""
        generator = CoverGenerator()
        title = "Test Magazine"
        author = "Publisher"

        image_bytes, ext = generator.generate_text_cover(title, author)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0
        assert ext == 'jpg'

        # Verify it's a valid image
        img = Image.open(io.BytesIO(image_bytes))
        assert img.size == (COVER_WIDTH, COVER_HEIGHT)
        assert img.mode == 'RGB'

    def test_generate_text_cover_with_date(self):
        """Test text cover with date."""
        generator = CoverGenerator()
        title = "Test Magazine"
        author = "Publisher"
        date = "January 2025"

        image_bytes, ext = generator.generate_text_cover(title, author, date)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0

    def test_generate_text_cover_no_author(self):
        """Test text cover without author."""
        generator = CoverGenerator()
        title = "Test Magazine"

        image_bytes, ext = generator.generate_text_cover(title)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0

    def test_generate_text_cover_long_title(self):
        """Test text cover with very long title (should wrap)."""
        generator = CoverGenerator()
        title = "This is a Very Long Magazine Title That Should Wrap Across Multiple Lines"

        image_bytes, ext = generator.generate_text_cover(title)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0


class TestGradientBackground:
    """Test gradient background generation."""

    def test_create_gradient_background(self):
        """Test gradient creation."""
        generator = CoverGenerator()
        gradient = generator._create_gradient_background(COVER_WIDTH, COVER_HEIGHT)

        assert gradient.size == (COVER_WIDTH, COVER_HEIGHT)
        assert gradient.mode == 'RGB'

        # Check top color is blue-ish
        top_pixel = gradient.getpixel((COVER_WIDTH // 2, 0))
        assert top_pixel[2] > top_pixel[1]  # More blue than green

        # Check bottom color is purple-ish
        bottom_pixel = gradient.getpixel((COVER_WIDTH // 2, COVER_HEIGHT - 1))
        assert bottom_pixel[0] > top_pixel[0]  # More red at bottom


class TestTextUtilities:
    """Test text wrapping and truncation utilities."""

    def test_truncate_short_text(self):
        """Test that short text is not truncated."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=False)
        text = "Short"

        result = generator._truncate_text(text, font, 1000)

        assert result == "Short"

    def test_truncate_long_text(self):
        """Test that long text is truncated with ellipsis."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=False)
        text = "This is a very long text that should definitely be truncated"

        result = generator._truncate_text(text, font, 200)

        assert result.endswith("...")
        assert len(result) < len(text)

    def test_wrap_text_single_line(self):
        """Test that short text stays on one line."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=False)
        text = "Short title"

        lines = generator._wrap_text(text, font, 1000)

        assert len(lines) == 1
        assert lines[0] == text

    def test_wrap_text_multiple_lines(self):
        """Test that long text wraps to multiple lines."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=False)
        text = "This is a very long magazine title that should wrap"

        lines = generator._wrap_text(text, font, 400)

        assert len(lines) > 1
        # All words should be preserved
        assert ' '.join(lines) == text


class TestFontHandling:
    """Test font loading and caching."""

    def test_get_font_regular(self):
        """Test loading regular font."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=False)

        assert font is not None

    def test_get_font_bold(self):
        """Test loading bold font."""
        generator = CoverGenerator()
        font = generator._get_font(48, bold=True)

        assert font is not None

    def test_font_caching(self):
        """Test that fonts are cached."""
        generator = CoverGenerator()

        font1 = generator._get_font(48, bold=False)
        font2 = generator._get_font(48, bold=False)

        assert font1 is font2  # Same object


class TestImageResizing:
    """Test image resizing and cropping."""

    def test_resize_and_crop_wide_image(self):
        """Test resizing and cropping wide image."""
        generator = CoverGenerator()

        # Create wide image
        img = Image.new('RGB', (1600, 800), (255, 0, 0))

        result = generator._resize_and_crop(img, 400, 400)

        assert result.size == (400, 400)

    def test_resize_and_crop_tall_image(self):
        """Test resizing and cropping tall image."""
        generator = CoverGenerator()

        # Create tall image
        img = Image.new('RGB', (800, 1600), (0, 255, 0))

        result = generator._resize_and_crop(img, 400, 400)

        assert result.size == (400, 400)

    def test_resize_and_crop_maintains_quality(self):
        """Test that resizing uses high-quality resampling."""
        generator = CoverGenerator()

        # Create test image with pattern
        img = Image.new('RGB', (1000, 1000), (128, 128, 128))

        result = generator._resize_and_crop(img, 500, 500)

        assert result.size == (500, 500)
        # Image should still be valid
        assert result.mode == 'RGB'


class TestMosaicCreation:
    """Test mosaic cover creation."""

    def create_test_image(self, width=800, height=600, color=(255, 0, 0)):
        """Helper to create test image."""
        return Image.new('RGB', (width, height), color)

    def test_create_mosaic_2_images(self):
        """Test mosaic with 2 images (2x1 layout - stacked horizontally)."""
        generator = CoverGenerator()
        images = [
            self.create_test_image(color=(255, 0, 0)),
            self.create_test_image(color=(0, 255, 0)),
        ]

        result = generator._create_mosaic(images, "Test Title", "Author")

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)
        assert result.mode == 'RGB'

    def test_create_mosaic_4_images(self):
        """Test mosaic with 4 images (2x2 layout)."""
        generator = CoverGenerator()
        images = [
            self.create_test_image(color=(255, 0, 0)),
            self.create_test_image(color=(0, 255, 0)),
            self.create_test_image(color=(0, 0, 255)),
            self.create_test_image(color=(255, 255, 0)),
        ]

        result = generator._create_mosaic(images, "Test Title", "Author")

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)
        assert result.mode == 'RGB'

    def test_create_mosaic_6_images(self):
        """Test mosaic with 6 images (3x2 layout - landscape cells)."""
        generator = CoverGenerator()
        images = [
            self.create_test_image(color=(255, 0, 0)),
            self.create_test_image(color=(0, 255, 0)),
            self.create_test_image(color=(0, 0, 255)),
            self.create_test_image(color=(255, 255, 0)),
            self.create_test_image(color=(255, 0, 255)),
            self.create_test_image(color=(0, 255, 255)),
        ]

        result = generator._create_mosaic(images, "Test Title", "Author")

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)
        assert result.mode == 'RGB'

    def test_create_mosaic_without_author(self):
        """Test mosaic creation without author."""
        generator = CoverGenerator()
        images = [
            self.create_test_image(color=(255, 0, 0)),
            self.create_test_image(color=(0, 255, 0)),
        ]

        result = generator._create_mosaic(images, "Test Title", None)

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)


class TestBannerAddition:
    """Test text banner addition to covers."""

    def test_add_text_banner(self):
        """Test adding text banner to image."""
        generator = CoverGenerator()

        # Create base image
        base = Image.new('RGB', (COVER_WIDTH, COVER_HEIGHT), (255, 255, 255))

        result = generator._add_text_banner(base, "Test Title", "Author")

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)
        assert result.mode == 'RGB'

    def test_add_text_banner_no_author(self):
        """Test adding banner without author."""
        generator = CoverGenerator()

        base = Image.new('RGB', (COVER_WIDTH, COVER_HEIGHT), (255, 255, 255))

        result = generator._add_text_banner(base, "Test Title", None)

        assert result.size == (COVER_WIDTH, COVER_HEIGHT)


class TestThumbnailDownload:
    """Test thumbnail downloading and processing."""

    @pytest.mark.asyncio
    async def test_download_thumbnails_success(self):
        """Test successful thumbnail download."""
        generator = CoverGenerator()

        # Create mock fetcher
        fetcher = AsyncMock()

        # Create test image bytes
        img = Image.new('RGB', (800, 600), (255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        # fetch_binary returns tuple: (data, final_url)
        fetcher.fetch_binary = AsyncMock(return_value=(img_bytes, "https://example.com/image.jpg"))

        # Mock process_image to return the same bytes
        with patch('gensi.core.cover_generator.process_image', return_value=(img_bytes, 'jpg')):
            urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
            images = await generator._download_thumbnails(urls, fetcher)

        assert len(images) == 2
        assert all(isinstance(img, Image.Image) for img in images)

    @pytest.mark.asyncio
    async def test_download_thumbnails_some_fail(self):
        """Test thumbnail download with some failures."""
        generator = CoverGenerator()

        # Create mock fetcher
        fetcher = AsyncMock()

        # Create test image bytes
        img = Image.new('RGB', (800, 600), (255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        # First succeeds, second fails
        # fetch_binary returns tuple: (data, final_url)
        async def mock_fetch(url, context):
            if "image1" in url:
                return (img_bytes, url)
            else:
                raise Exception("Download failed")

        fetcher.fetch_binary = mock_fetch

        with patch('gensi.core.cover_generator.process_image', return_value=(img_bytes, 'jpg')):
            urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
            images = await generator._download_thumbnails(urls, fetcher)

        # Should have 1 successful image
        assert len(images) == 1

    @pytest.mark.asyncio
    async def test_download_thumbnails_all_fail(self):
        """Test thumbnail download when all fail."""
        generator = CoverGenerator()

        fetcher = AsyncMock()
        fetcher.fetch_binary = AsyncMock(side_effect=Exception("Download failed"))

        urls = ["https://example.com/image1.jpg"]
        images = await generator._download_thumbnails(urls, fetcher)

        assert len(images) == 0


class TestGenerateFromThumbnails:
    """Test complete cover generation from thumbnails."""

    @pytest.mark.asyncio
    async def test_generate_with_sufficient_thumbnails(self):
        """Test generation with 2+ thumbnails."""
        generator = CoverGenerator()

        # Create mock images
        img = Image.new('RGB', (800, 600), (255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        fetcher = AsyncMock()
        fetcher.fetch_binary = AsyncMock(return_value=img_bytes)

        with patch('gensi.core.cover_generator.process_image', return_value=(img_bytes, 'jpg')):
            urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
            cover_bytes, ext = await generator.generate_from_thumbnails(
                urls, "Test Title", "Author", fetcher, fallback_to_text=True
            )

        assert isinstance(cover_bytes, bytes)
        assert len(cover_bytes) > 0
        assert ext == 'jpg'

        # Verify it's a valid image
        cover_img = Image.open(io.BytesIO(cover_bytes))
        assert cover_img.size == (COVER_WIDTH, COVER_HEIGHT)

    @pytest.mark.asyncio
    async def test_generate_fallback_to_text(self):
        """Test fallback to text cover when insufficient thumbnails."""
        generator = CoverGenerator()

        fetcher = AsyncMock()
        fetcher.fetch_binary = AsyncMock(side_effect=Exception("Download failed"))

        urls = ["https://example.com/image1.jpg"]
        cover_bytes, ext = await generator.generate_from_thumbnails(
            urls, "Test Title", "Author", fetcher, fallback_to_text=True
        )

        # Should generate text cover
        assert isinstance(cover_bytes, bytes)
        assert len(cover_bytes) > 0
        assert ext == 'jpg'

    @pytest.mark.asyncio
    async def test_generate_no_fallback_raises_exception(self):
        """Test that exception is raised when fallback disabled and no thumbnails."""
        generator = CoverGenerator()

        fetcher = AsyncMock()
        fetcher.fetch_binary = AsyncMock(side_effect=Exception("Download failed"))

        urls = ["https://example.com/image1.jpg"]

        with pytest.raises(Exception, match="No thumbnails available"):
            await generator.generate_from_thumbnails(
                urls, "Test Title", "Author", fetcher, fallback_to_text=False
            )

    @pytest.mark.asyncio
    async def test_generate_single_thumbnail_fallback(self):
        """Test fallback to text when only 1 thumbnail (<2 minimum)."""
        generator = CoverGenerator()

        # Create one successful image
        img = Image.new('RGB', (800, 600), (255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        fetcher = AsyncMock()
        fetcher.fetch_binary = AsyncMock(return_value=img_bytes)

        with patch('gensi.core.cover_generator.process_image', return_value=(img_bytes, 'jpg')):
            urls = ["https://example.com/image1.jpg"]
            cover_bytes, ext = await generator.generate_from_thumbnails(
                urls, "Test Title", "Author", fetcher, fallback_to_text=True
            )

        # Should generate text cover (need 2+ for mosaic)
        assert isinstance(cover_bytes, bytes)
        assert len(cover_bytes) > 0
