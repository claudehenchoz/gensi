"""Tests to verify cover image extensions are correctly preserved."""

import tempfile
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from PIL import Image
import pytest

from gensi.core.processor import process_gensi_file


class TestCoverExtension:
    """Test that cover image extensions are correctly preserved after processing."""

    @pytest.mark.asyncio
    async def test_png_cover_keeps_png_extension(self, httpserver):
        """Test that a PNG cover image is saved as cover.png, not cover.jpg."""
        # Create a PNG image with transparency
        img = Image.new('RGBA', (500, 700), color=(255, 0, 0, 200))
        png_buffer = BytesIO()
        img.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()

        # Setup mock server
        httpserver.expect_request('/cover.png').respond_with_data(
            png_data,
            content_type='image/png'
        )
        httpserver.expect_request('/index.html').respond_with_data(
            '<html><body><a href="/article1.html">Article 1</a></body></html>'
        )
        httpserver.expect_request('/article1.html').respond_with_data(
            '<html><body><article>Content</article></body></html>'
        )

        # Create .gensi file
        gensi_content = f'''
title = "Test PNG Cover"

[cover]
url = "{httpserver.url_for('/cover.png')}"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a"

[article]
content = "article"
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            gensi_file = tmpdir / 'test.gensi'
            gensi_file.write_text(gensi_content)

            # Process
            epub_path = await process_gensi_file(gensi_file)

            # Verify EPUB was created
            assert epub_path.exists()

            # Open EPUB and check cover filename
            with ZipFile(epub_path, 'r') as epub:
                file_list = epub.namelist()

                # Should have EPUB/cover.png, not EPUB/cover.jpg
                assert 'EPUB/cover.png' in file_list, f"Expected EPUB/cover.png in EPUB, got: {file_list}"
                assert 'EPUB/cover.jpg' not in file_list, f"Should not have EPUB/cover.jpg in EPUB when source is PNG"

                # Verify the cover data is actually PNG
                cover_data = epub.read('EPUB/cover.png')
                cover_img = Image.open(BytesIO(cover_data))
                assert cover_img.format == 'PNG', "Cover should be in PNG format"

    @pytest.mark.asyncio
    async def test_jpeg_cover_keeps_jpeg_extension(self, httpserver):
        """Test that a JPEG cover image is saved as cover.jpg."""
        # Create a JPEG image
        img = Image.new('RGB', (500, 700), color='blue')
        jpg_buffer = BytesIO()
        img.save(jpg_buffer, format='JPEG', quality=90)
        jpg_data = jpg_buffer.getvalue()

        # Setup mock server
        httpserver.expect_request('/cover.jpg').respond_with_data(
            jpg_data,
            content_type='image/jpeg'
        )
        httpserver.expect_request('/index.html').respond_with_data(
            '<html><body><a href="/article1.html">Article 1</a></body></html>'
        )
        httpserver.expect_request('/article1.html').respond_with_data(
            '<html><body><article>Content</article></body></html>'
        )

        # Create .gensi file
        gensi_content = f'''
title = "Test JPEG Cover"

[cover]
url = "{httpserver.url_for('/cover.jpg')}"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a"

[article]
content = "article"
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            gensi_file = tmpdir / 'test.gensi'
            gensi_file.write_text(gensi_content)

            # Process
            epub_path = await process_gensi_file(gensi_file)

            # Verify EPUB was created
            assert epub_path.exists()

            # Open EPUB and check cover filename
            with ZipFile(epub_path, 'r') as epub:
                file_list = epub.namelist()

                # Should have EPUB/cover.jpg
                assert 'EPUB/cover.jpg' in file_list, f"Expected EPUB/cover.jpg in EPUB, got: {file_list}"

                # Verify the cover data is actually JPEG
                cover_data = epub.read('EPUB/cover.jpg')
                cover_img = Image.open(BytesIO(cover_data))
                assert cover_img.format == 'JPEG', "Cover should be in JPEG format"

    @pytest.mark.asyncio
    async def test_webp_cover_with_transparency_becomes_png(self, httpserver):
        """Test that a WebP cover with transparency is converted to PNG."""
        # Create a WebP image with transparency
        img = Image.new('RGBA', (500, 700), color=(0, 255, 0, 150))
        webp_buffer = BytesIO()
        img.save(webp_buffer, format='WEBP')
        webp_data = webp_buffer.getvalue()

        # Setup mock server
        httpserver.expect_request('/cover.webp').respond_with_data(
            webp_data,
            content_type='image/webp'
        )
        httpserver.expect_request('/index.html').respond_with_data(
            '<html><body><a href="/article1.html">Article 1</a></body></html>'
        )
        httpserver.expect_request('/article1.html').respond_with_data(
            '<html><body><article>Content</article></body></html>'
        )

        # Create .gensi file
        gensi_content = f'''
title = "Test WebP Cover"

[cover]
url = "{httpserver.url_for('/cover.webp')}"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a"

[article]
content = "article"
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            gensi_file = tmpdir / 'test.gensi'
            gensi_file.write_text(gensi_content)

            # Process
            epub_path = await process_gensi_file(gensi_file)

            # Verify EPUB was created
            assert epub_path.exists()

            # Open EPUB and check cover filename
            with ZipFile(epub_path, 'r') as epub:
                file_list = epub.namelist()

                # WebP with transparency should become PNG
                assert 'EPUB/cover.png' in file_list, f"Expected EPUB/cover.png (from webp with transparency), got: {file_list}"
                assert 'EPUB/cover.webp' not in file_list, "WebP should be converted"

                # Verify the cover data is PNG with transparency
                cover_data = epub.read('EPUB/cover.png')
                cover_img = Image.open(BytesIO(cover_data))
                assert cover_img.format == 'PNG', "Cover should be converted to PNG"
                assert cover_img.mode == 'RGBA', "PNG should preserve transparency"

    def test_webp_opaque_conversion_logic(self):
        """Test that opaque WebP images are correctly identified and converted to JPEG."""
        from gensi.core.image_optimizer import process_image

        # Create an opaque WebP image (RGB, no transparency)
        img = Image.new('RGB', (500, 700), color='purple')
        webp_buffer = BytesIO()
        # Force lossy RGB WebP
        img.save(webp_buffer, format='WEBP', lossless=False, quality=80)
        webp_data = webp_buffer.getvalue()

        # Verify it's RGB
        test_img = Image.open(BytesIO(webp_data))
        assert test_img.mode == 'RGB', f"Source WebP should be RGB, got {test_img.mode}"

        # Process the image
        processed_data, extension = process_image(
            webp_data,
            'http://example.com/cover.webp',
            image_type='cover'
        )

        # Should be converted to JPEG
        assert extension == 'jpg', f"Expected 'jpg' extension, got '{extension}'"

        # Verify output is actually JPEG
        result_img = Image.open(BytesIO(processed_data))
        assert result_img.format == 'JPEG', "Output should be JPEG format"
        assert result_img.mode == 'RGB', "Output should be RGB mode"
