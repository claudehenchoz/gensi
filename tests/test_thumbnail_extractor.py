"""Tests for thumbnail extraction module."""

import pytest
from lxml import html
from gensi.utils.thumbnail_extractor import (
    extract_thumbnails,
    _extract_from_meta_tags,
    _extract_from_jsonld,
    _extract_from_body,
    _score_image,
    _deduplicate_thumbnails,
    ThumbnailCandidate
)


class TestMetaTagExtraction:
    """Test extraction from Open Graph and Twitter Card meta tags."""

    @pytest.fixture
    def html_with_og_image(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/og-image.jpg" />
    <meta property="og:title" content="Test Article" />
</head>
<body>
    <h1>Article</h1>
</body>
</html>
"""

    @pytest.fixture
    def html_with_twitter_image(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta name="twitter:image" content="https://example.com/twitter-image.jpg" />
    <meta name="twitter:card" content="summary_large_image" />
</head>
<body>
    <h1>Article</h1>
</body>
</html>
"""

    @pytest.fixture
    def html_with_multiple_meta(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/og.jpg" />
    <meta name="twitter:image" content="https://example.com/twitter.jpg" />
    <meta property="article:image" content="https://example.com/article.jpg" />
    <link rel="image_src" href="https://example.com/link.jpg" />
</head>
<body></body>
</html>
"""

    def test_extract_og_image(self, html_with_og_image):
        """Test extraction of og:image meta tag."""
        doc = html.fromstring(html_with_og_image)
        candidates = _extract_from_meta_tags(doc)

        assert len(candidates) == 1
        assert candidates[0].url == "https://example.com/og-image.jpg"
        assert candidates[0].source == 'meta'
        assert candidates[0].score == 10.0

    def test_extract_twitter_image(self, html_with_twitter_image):
        """Test extraction of twitter:image meta tag."""
        doc = html.fromstring(html_with_twitter_image)
        candidates = _extract_from_meta_tags(doc)

        assert len(candidates) == 1
        assert candidates[0].url == "https://example.com/twitter-image.jpg"
        assert candidates[0].source == 'meta'
        assert candidates[0].score == 10.0

    def test_extract_multiple_meta_tags(self, html_with_multiple_meta):
        """Test extraction of multiple meta tags."""
        doc = html.fromstring(html_with_multiple_meta)
        candidates = _extract_from_meta_tags(doc)

        assert len(candidates) == 4
        urls = [c.url for c in candidates]
        assert "https://example.com/og.jpg" in urls
        assert "https://example.com/twitter.jpg" in urls
        assert "https://example.com/article.jpg" in urls
        assert "https://example.com/link.jpg" in urls

    def test_no_meta_tags(self):
        """Test when no meta tags are present."""
        html_str = "<html><head></head><body></body></html>"
        doc = html.fromstring(html_str)
        candidates = _extract_from_meta_tags(doc)

        assert len(candidates) == 0


class TestJSONLDExtraction:
    """Test extraction from JSON-LD structured data."""

    @pytest.fixture
    def html_with_article_jsonld(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Test Article",
        "image": "https://example.com/jsonld-image.jpg",
        "author": "John Doe"
    }
    </script>
</head>
<body></body>
</html>
"""

    @pytest.fixture
    def html_with_image_array(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Test",
        "image": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    }
    </script>
</head>
<body></body>
</html>
"""

    @pytest.fixture
    def html_with_image_object(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "image": {
            "@type": "ImageObject",
            "url": "https://example.com/image-object.jpg",
            "width": 1200,
            "height": 800
        }
    }
    </script>
</head>
<body></body>
</html>
"""

    def test_extract_from_article_jsonld(self, html_with_article_jsonld):
        """Test extraction from NewsArticle JSON-LD."""
        doc = html.fromstring(html_with_article_jsonld)
        candidates = _extract_from_jsonld(doc)

        assert len(candidates) == 1
        assert candidates[0].url == "https://example.com/jsonld-image.jpg"
        assert candidates[0].source == 'jsonld'
        assert candidates[0].score == 9.0

    def test_extract_image_array(self, html_with_image_array):
        """Test extraction when image is an array."""
        doc = html.fromstring(html_with_image_array)
        candidates = _extract_from_jsonld(doc)

        assert len(candidates) == 2
        urls = [c.url for c in candidates]
        assert "https://example.com/image1.jpg" in urls
        assert "https://example.com/image2.jpg" in urls

    def test_extract_image_object(self, html_with_image_object):
        """Test extraction when image is ImageObject."""
        doc = html.fromstring(html_with_image_object)
        candidates = _extract_from_jsonld(doc)

        assert len(candidates) >= 1
        urls = [c.url for c in candidates]
        assert "https://example.com/image-object.jpg" in urls

    def test_no_jsonld(self):
        """Test when no JSON-LD is present."""
        html_str = "<html><head></head><body></body></html>"
        doc = html.fromstring(html_str)
        candidates = _extract_from_jsonld(doc)

        assert len(candidates) == 0


class TestBodyImageExtraction:
    """Test extraction from <img> tags in body."""

    @pytest.fixture
    def html_with_large_image(self):
        return """
<!DOCTYPE html>
<html>
<body>
    <img src="https://example.com/large.jpg" width="800" height="600" alt="Large image" />
</body>
</html>
"""

    @pytest.fixture
    def html_with_small_icon(self):
        return """
<!DOCTYPE html>
<html>
<body>
    <img src="https://example.com/icon.png" width="32" height="32" class="icon" />
</body>
</html>
"""

    @pytest.fixture
    def html_with_featured_image(self):
        return """
<!DOCTYPE html>
<html>
<body>
    <figure>
        <img src="https://example.com/featured.jpg" class="featured-image" width="1200" height="800" />
    </figure>
</body>
</html>
"""

    @pytest.fixture
    def html_with_ad_image(self):
        return """
<!DOCTYPE html>
<html>
<body>
    <img src="https://ads.example.com/banner.jpg" class="ad-banner" width="728" height="90" />
</body>
</html>
"""

    def test_extract_large_image(self, html_with_large_image):
        """Test extraction of large image."""
        doc = html.fromstring(html_with_large_image)
        candidates = _extract_from_body(doc, "https://example.com/")

        assert len(candidates) >= 1
        assert candidates[0].url == "https://example.com/large.jpg"
        assert candidates[0].score > 5.0  # Should have positive score

    def test_skip_small_icon(self, html_with_small_icon):
        """Test that small icons are filtered out."""
        doc = html.fromstring(html_with_small_icon)
        candidates = _extract_from_body(doc, "https://example.com/")

        # Icon should have negative score and be filtered
        assert len(candidates) == 0

    def test_boost_featured_image(self, html_with_featured_image):
        """Test that featured images get score boost."""
        doc = html.fromstring(html_with_featured_image)
        candidates = _extract_from_body(doc, "https://example.com/")

        assert len(candidates) >= 1
        # Should have high score due to dimensions + figure + class
        assert candidates[0].score > 10.0

    def test_filter_ad_image(self, html_with_ad_image):
        """Test that ad images are filtered out."""
        doc = html.fromstring(html_with_ad_image)
        candidates = _extract_from_body(doc, "https://example.com/")

        # Ad should have negative score
        assert len(candidates) == 0


class TestImageScoring:
    """Test image quality scoring algorithm."""

    def test_base_score(self):
        """Test base score for simple image."""
        html_str = '<img src="test.jpg" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        assert score == 5.0  # Base score

    def test_dimension_boosters(self):
        """Test score boosters for large dimensions."""
        html_str = '<img src="test.jpg" width="800" height="600" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Base (5) + width boost (3) + height boost (3) + has dimensions (1) = 12
        assert score == 12.0

    def test_dimension_penalties(self):
        """Test score penalties for small dimensions."""
        html_str = '<img src="test.jpg" width="100" height="100" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Base (5) + has dimensions (1) - width penalty (5) - height penalty (5) = -4
        assert score < 0

    def test_figure_context_boost(self):
        """Test score boost for images in figure tags."""
        html_str = '<figure><img src="test.jpg" width="800" height="600" /></figure>'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Should include figure boost (+2)
        assert score >= 14.0  # Base + dims + figure

    def test_featured_class_boost(self):
        """Test score boost for featured/hero classes."""
        html_str = '<img src="test.jpg" class="featured-image" width="800" height="600" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Should include class boost (+2)
        assert score >= 14.0

    def test_icon_class_penalty(self):
        """Test score penalty for icon classes."""
        html_str = '<img src="test.jpg" class="icon" width="800" height="600" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Should have large negative penalty
        assert score < 0

    def test_data_url_penalty(self):
        """Test score penalty for data URLs."""
        html_str = '<img src="data:image/png;base64,iVBORw0KG..." width="800" height="600" />'
        doc = html.fromstring(html_str)
        img = doc.xpath('//img')[0]

        score = _score_image(img, "https://example.com/")
        # Should have data URL penalty
        assert score < 0


class TestDeduplication:
    """Test thumbnail deduplication."""

    def test_deduplicate_exact_duplicates(self):
        """Test removal of exact duplicate URLs."""
        candidates = [
            ThumbnailCandidate("https://example.com/image.jpg", "meta", 10.0),
            ThumbnailCandidate("https://example.com/image.jpg", "body", 5.0),
        ]

        result = _deduplicate_thumbnails(candidates)

        assert len(result) == 1
        assert result[0].score == 10.0  # Keep higher score

    def test_deduplicate_query_param_variants(self):
        """Test deduplication of URLs with different query params."""
        candidates = [
            ThumbnailCandidate("https://example.com/image.jpg?v=1", "meta", 10.0),
            ThumbnailCandidate("https://example.com/image.jpg?v=2", "body", 5.0),
        ]

        result = _deduplicate_thumbnails(candidates)

        # Should recognize as same image and keep highest score
        assert len(result) == 1
        assert result[0].score == 10.0

    def test_keep_different_urls(self):
        """Test that different URLs are not deduplicated."""
        candidates = [
            ThumbnailCandidate("https://example.com/image1.jpg", "meta", 10.0),
            ThumbnailCandidate("https://example.com/image2.jpg", "body", 5.0),
        ]

        result = _deduplicate_thumbnails(candidates)

        assert len(result) == 2


class TestExtractThumbnailsIntegration:
    """Integration tests for the main extract_thumbnails function."""

    @pytest.fixture
    def html_with_all_sources(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://example.com/og.jpg" />
    <script type="application/ld+json">
    {
        "@type": "Article",
        "image": "https://example.com/jsonld.jpg"
    }
    </script>
</head>
<body>
    <article>
        <img src="https://example.com/body.jpg" width="800" height="600" class="featured" />
    </article>
</body>
</html>
"""

    def test_extract_from_all_sources(self, html_with_all_sources):
        """Test extraction from multiple sources."""
        doc = html.fromstring(html_with_all_sources)
        thumbnails = extract_thumbnails(doc, "https://example.com/", max_count=10)

        # Should find images from meta, jsonld, and body
        assert len(thumbnails) >= 3
        assert all(isinstance(url, str) for url in thumbnails)
        assert all(url.startswith("http") for url in thumbnails)

    def test_max_count_limit(self):
        """Test that max_count parameter limits results."""
        html_str = """
<html><body>
    <img src="img1.jpg" width="800" height="600" />
    <img src="img2.jpg" width="800" height="600" />
    <img src="img3.jpg" width="800" height="600" />
    <img src="img4.jpg" width="800" height="600" />
    <img src="img5.jpg" width="800" height="600" />
</body></html>
"""
        doc = html.fromstring(html_str)
        thumbnails = extract_thumbnails(doc, "https://example.com/", max_count=3)

        assert len(thumbnails) == 3

    def test_url_resolution(self):
        """Test that relative URLs are resolved to absolute."""
        html_str = '<html><head><meta property="og:image" content="/images/og.jpg" /></head></html>'
        doc = html.fromstring(html_str)
        thumbnails = extract_thumbnails(doc, "https://example.com/", max_count=10)

        assert len(thumbnails) >= 1
        assert thumbnails[0] == "https://example.com/images/og.jpg"

    def test_empty_document(self):
        """Test extraction from empty document."""
        html_str = "<html><head></head><body></body></html>"
        doc = html.fromstring(html_str)
        thumbnails = extract_thumbnails(doc, "https://example.com/", max_count=10)

        assert len(thumbnails) == 0

    def test_ordering_by_score(self):
        """Test that results are ordered by score (meta > jsonld > body)."""
        html_str = """
<html>
<head>
    <meta property="og:image" content="https://example.com/meta.jpg" />
</head>
<body>
    <img src="https://example.com/body.jpg" width="50" height="50" />
</body>
</html>
"""
        doc = html.fromstring(html_str)
        thumbnails = extract_thumbnails(doc, "https://example.com/", max_count=10)

        # Meta image should come first (higher score)
        assert thumbnails[0] == "https://example.com/meta.jpg"
