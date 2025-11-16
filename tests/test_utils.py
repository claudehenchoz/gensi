"""Tests for utility functions - URL resolution and metadata fallback."""

import pytest
from lxml import html
from gensi.utils.url_utils import resolve_url, is_image_url, get_base_url
from gensi.utils.metadata_fallback import extract_metadata_fallback


class TestURLUtils:
    """Test URL utility functions."""

    def test_resolve_absolute_url(self):
        """Test resolving already absolute URL."""
        base = "http://example.com/page"
        url = "http://other.com/image.jpg"

        result = resolve_url(base, url)
        assert result == "http://other.com/image.jpg"

    def test_resolve_relative_url_path(self):
        """Test resolving relative path URL."""
        base = "http://example.com/articles/page.html"
        url = "/images/photo.jpg"

        result = resolve_url(base, url)
        assert result == "http://example.com/images/photo.jpg"

    def test_resolve_relative_url_same_dir(self):
        """Test resolving relative URL in same directory."""
        base = "http://example.com/articles/page.html"
        url = "photo.jpg"

        result = resolve_url(base, url)
        assert result == "http://example.com/articles/photo.jpg"

    def test_resolve_relative_url_parent_dir(self):
        """Test resolving relative URL with parent directory."""
        base = "http://example.com/articles/2025/page.html"
        url = "../images/photo.jpg"

        result = resolve_url(base, url)
        assert result == "http://example.com/articles/images/photo.jpg"

    def test_resolve_protocol_relative_url(self):
        """Test resolving protocol-relative URL."""
        base = "https://example.com/page"
        url = "//other.com/image.jpg"

        result = resolve_url(base, url)
        assert result == "https://other.com/image.jpg"

    def test_resolve_url_with_query(self):
        """Test resolving URL with query parameters."""
        base = "http://example.com/page"
        url = "/api/data?id=123"

        result = resolve_url(base, url)
        assert result == "http://example.com/api/data?id=123"

    def test_resolve_url_with_fragment(self):
        """Test resolving URL with fragment."""
        base = "http://example.com/page"
        url = "#section"

        result = resolve_url(base, url)
        assert result == "http://example.com/page#section"

    def test_is_image_url_jpg(self):
        """Test detecting JPG image URL."""
        assert is_image_url("http://example.com/photo.jpg") is True
        assert is_image_url("http://example.com/photo.jpeg") is True
        assert is_image_url("http://example.com/photo.JPG") is True

    def test_is_image_url_png(self):
        """Test detecting PNG image URL."""
        assert is_image_url("http://example.com/image.png") is True
        assert is_image_url("http://example.com/image.PNG") is True

    def test_is_image_url_other_formats(self):
        """Test detecting other image formats."""
        assert is_image_url("http://example.com/anim.gif") is True
        assert is_image_url("http://example.com/photo.webp") is True
        assert is_image_url("http://example.com/logo.svg") is True

    def test_is_image_url_not_image(self):
        """Test non-image URLs."""
        assert is_image_url("http://example.com/page.html") is False
        assert is_image_url("http://example.com/style.css") is False
        assert is_image_url("http://example.com/script.js") is False
        assert is_image_url("http://example.com/") is False

    def test_is_image_url_with_query(self):
        """Test detecting image URL with query parameters."""
        assert is_image_url("http://example.com/photo.jpg?size=large") is True

    def test_get_base_url(self):
        """Test extracting base URL."""
        url = "http://example.com/articles/2025/page.html"
        base = get_base_url(url)

        assert base == "http://example.com"

    def test_get_base_url_with_port(self):
        """Test extracting base URL with port."""
        url = "http://example.com:8080/page.html"
        base = get_base_url(url)

        assert base == "http://example.com:8080"


class TestMetadataFallback:
    """Test metadata fallback extraction."""

    def test_extract_title_from_og_title(self):
        """Test extracting title from og:title meta tag."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="OpenGraph Title">
    <title>HTML Title</title>
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "OpenGraph Title"

    def test_extract_title_from_twitter_title(self):
        """Test extracting title from twitter:title meta tag."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta name="twitter:title" content="Twitter Title">
    <title>HTML Title</title>
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "Twitter Title"

    def test_extract_title_from_title_tag(self):
        """Test extracting title from <title> tag."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>HTML Title</title>
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "HTML Title"

    def test_extract_title_from_h1(self):
        """Test extracting title from h1 tag as last fallback."""
        html_content = """
<!DOCTYPE html>
<html>
<head></head>
<body>
    <h1>H1 Title</h1>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "H1 Title"

    def test_extract_title_precedence(self):
        """Test that og:title takes precedence over twitter:title."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="OG Title">
    <meta name="twitter:title" content="Twitter Title">
    <title>HTML Title</title>
</head>
<body>
    <h1>H1 Title</h1>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "OG Title"

    def test_extract_author_from_meta(self):
        """Test extracting author from meta tag."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta name="author" content="John Doe">
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['author'] == "John Doe"

    def test_extract_author_from_article_author(self):
        """Test extracting author from article:author meta tag."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="article:author" content="Jane Smith">
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['author'] == "Jane Smith"

    def test_extract_date_from_article_published_time(self):
        """Test extracting date from article:published_time."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="article:published_time" content="2025-01-15T10:00:00Z">
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['date'] == "2025-01-15T10:00:00Z"

    def test_extract_date_from_time_datetime(self):
        """Test extracting date from time element datetime attribute."""
        html_content = """
<!DOCTYPE html>
<html>
<head></head>
<body>
    <time datetime="2025-01-15">January 15, 2025</time>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['date'] == "2025-01-15"

    def test_extract_all_metadata(self):
        """Test extracting all metadata fields."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="Article Title">
    <meta name="author" content="Test Author">
    <meta property="article:published_time" content="2025-01-15T10:00:00Z">
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] == "Article Title"
        assert metadata['author'] == "Test Author"
        assert metadata['date'] == "2025-01-15T10:00:00Z"

    def test_extract_with_missing_metadata(self):
        """Test extracting when no metadata is present."""
        html_content = """
<!DOCTYPE html>
<html>
<head></head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        assert metadata['title'] is None
        assert metadata['author'] is None
        assert metadata['date'] is None

    def test_extract_with_empty_values(self):
        """Test extracting when metadata tags are empty."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="">
    <meta name="author" content="">
</head>
<body></body>
</html>
"""
        doc = html.fromstring(html_content)
        metadata = extract_metadata_fallback(doc, "http://example.com")

        # Empty values should be treated as None or fall back
        assert metadata['title'] is None or metadata['title'] == ""
        assert metadata['author'] is None or metadata['author'] == ""
