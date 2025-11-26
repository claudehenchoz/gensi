"""Integration tests for automatic cover generation."""

import pytest
from pathlib import Path
from gensi.core.processor import process_gensi_file
from tests.helpers.epub_validator import validate_epub_structure


@pytest.mark.asyncio
class TestAutoCoverIntegration:
    """Test automatic cover generation from article thumbnails."""

    async def test_auto_cover_with_og_images(self, temp_dir, httpserver):
        """Test auto-cover generation from og:image meta tags."""
        # Serve index page
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <div class="articles">
        <a href="/article1.html" class="article-link">Article 1</a>
        <a href="/article2.html" class="article-link">Article 2</a>
    </div>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # Serve articles with og:image meta tags
        article1_html = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/thumb1.jpg" />
    <title>Article 1</title>
</head>
<body>
    <h1>Article 1</h1>
    <div class="content">Content of article 1</div>
</body>
</html>
"""
        article2_html = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/thumb2.jpg" />
    <title>Article 2</title>
</head>
<body>
    <h1>Article 2</h1>
    <div class="content">Content of article 2</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(article1_html, content_type="text/html")
        httpserver.expect_request("/article2.html").respond_with_data(article2_html, content_type="text/html")

        # Serve dummy thumbnail images (will fail but that's OK - will fall back to text cover)
        httpserver.expect_request("/thumb1.jpg").respond_with_data(b"dummy", status=404)
        httpserver.expect_request("/thumb2.jpg").respond_with_data(b"dummy", status=404)

        # Create .gensi file WITHOUT [cover] section
        gensi_content = f"""
title = "Test Magazine"
author = "Test Publisher"
language = "en"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.article-link"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_auto_cover.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Verify EPUB was created
        assert output_path.exists()

        # Validate EPUB structure
        results = validate_epub_structure(output_path)
        assert results['valid'] is True

        # Verify cover exists (either mosaic or text fallback)
        assert results['has_cover'] is True

    async def test_auto_cover_text_fallback(self, temp_dir, httpserver):
        """Test text-only cover generation when no thumbnails available."""
        # Serve index page
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <div class="articles">
        <a href="/article1.html" class="article-link">Article 1</a>
    </div>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # Serve article WITHOUT og:image (no thumbnails)
        article1_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Article 1</title>
</head>
<body>
    <h1>Article 1</h1>
    <div class="content">Content without images</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(article1_html, content_type="text/html")

        # Create .gensi file WITHOUT [cover] section
        gensi_content = f"""
title = "Text Cover Test"
author = "Test Publisher"
language = "en"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.article-link"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_text_cover.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Verify EPUB was created
        assert output_path.exists()

        # Validate EPUB structure
        results = validate_epub_structure(output_path)
        assert results['valid'] is True

        # Should have a text cover
        assert results['has_cover'] is True

    async def test_explicit_cover_disables_auto_cover(self, temp_dir, httpserver):
        """Test that explicit [cover] section disables auto-cover generation."""
        # Serve index page
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <div class="articles">
        <a href="/article1.html" class="article-link">Article 1</a>
    </div>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # Serve article with og:image
        article1_html = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/thumb.jpg" />
    <title>Article 1</title>
</head>
<body>
    <h1>Article 1</h1>
    <div class="content">Content</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(article1_html, content_type="text/html")

        # Serve explicit cover image
        import io
        from PIL import Image
        cover_img = Image.new('RGB', (400, 600), (255, 0, 0))
        cover_bytes = io.BytesIO()
        cover_img.save(cover_bytes, format='JPEG')
        cover_bytes = cover_bytes.getvalue()

        httpserver.expect_request("/explicit_cover.jpg").respond_with_data(cover_bytes, content_type="image/jpeg")

        # Create .gensi file WITH explicit [cover] section
        gensi_content = f"""
title = "Explicit Cover Test"
author = "Test Publisher"
language = "en"

[cover]
url = "{httpserver.url_for('/explicit_cover.jpg')}"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.article-link"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_explicit_cover.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Verify EPUB was created
        assert output_path.exists()

        # Validate EPUB structure
        results = validate_epub_structure(output_path)
        assert results['valid'] is True

        # Should have cover from explicit definition, not auto-generated
        assert results['has_cover'] is True

    async def test_auto_cover_with_body_images(self, temp_dir, httpserver):
        """Test auto-cover extraction from body images (not just meta tags)."""
        # Serve index page
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <a href="/article1.html" class="link">Article 1</a>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # Serve article with large featured image in body (no og:image)
        article1_html = """
<!DOCTYPE html>
<html>
<head><title>Article 1</title></head>
<body>
    <h1>Article 1</h1>
    <figure>
        <img src="/featured.jpg" class="featured-image" width="1200" height="800" alt="Featured" />
    </figure>
    <div class="content">Content here</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(article1_html, content_type="text/html")

        # Mock featured image (will fail, fallback to text)
        httpserver.expect_request("/featured.jpg").respond_with_data(b"dummy", status=404)

        # Create .gensi file WITHOUT [cover] section
        gensi_content = f"""
title = "Body Image Test"
author = "Test Publisher"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.link"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_body_images.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Verify EPUB was created with auto-cover
        assert output_path.exists()
        results = validate_epub_structure(output_path)
        assert results['valid'] is True
        assert results['has_cover'] is True

    async def test_auto_cover_deduplication(self, temp_dir, httpserver):
        """Test that duplicate thumbnails are deduplicated."""
        # Serve index page with multiple articles
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <a href="/article1.html">Article 1</a>
    <a href="/article2.html">Article 2</a>
    <a href="/article3.html">Article 3</a>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # All articles use the SAME og:image (should deduplicate)
        article_template = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/same_thumb.jpg" />
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">Content</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(
            article_template.format(title="Article 1"), content_type="text/html"
        )
        httpserver.expect_request("/article2.html").respond_with_data(
            article_template.format(title="Article 2"), content_type="text/html"
        )
        httpserver.expect_request("/article3.html").respond_with_data(
            article_template.format(title="Article 3"), content_type="text/html"
        )

        # Create .gensi file
        gensi_content = f"""
title = "Deduplication Test"
author = "Publisher"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_dedup.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Should successfully create EPUB with cover (deduplication happens internally)
        assert output_path.exists()
        results = validate_epub_structure(output_path)
        assert results['valid'] is True
        assert results['has_cover'] is True


@pytest.mark.asyncio
class TestAutoCoverJSONLD:
    """Test auto-cover extraction from JSON-LD structured data."""

    async def test_auto_cover_from_jsonld(self, temp_dir, httpserver):
        """Test extracting thumbnails from JSON-LD schema.org data."""
        # Serve index page
        index_html = """
<!DOCTYPE html>
<html>
<body>
    <a href="/article1.html">Article 1</a>
</body>
</html>
"""
        httpserver.expect_request("/index.html").respond_with_data(index_html, content_type="text/html")

        # Serve article with JSON-LD (no og:image meta tag)
        article1_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Article 1</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Article 1",
        "image": "https://example.com/jsonld_thumb.jpg",
        "author": "John Doe"
    }
    </script>
</head>
<body>
    <h1>Article 1</h1>
    <div class="content">Content</div>
</body>
</html>
"""
        httpserver.expect_request("/article1.html").respond_with_data(article1_html, content_type="text/html")

        # Create .gensi file WITHOUT [cover] section
        gensi_content = f"""
title = "JSON-LD Test"
author = "Publisher"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a"

[article]
content = "div.content"
title = "h1"
"""
        gensi_path = temp_dir / 'test_jsonld.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Should create EPUB with auto-cover (from JSON-LD)
        assert output_path.exists()
        results = validate_epub_structure(output_path)
        assert results['valid'] is True
        assert results['has_cover'] is True
