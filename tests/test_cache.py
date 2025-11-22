"""Tests for HTTP caching functionality."""

import asyncio
import tempfile
from pathlib import Path
import pytest

from gensi.core.cache import HttpCache
from gensi.core.cached_fetcher import CachedFetcher


class TestHttpCache:
    """Test the HttpCache class."""

    def test_cache_init_default_location(self):
        """Test cache initialization with default location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")
            assert cache.cache_dir.exists()
            cache.close()

    def test_cache_set_and_get_text(self):
        """Test setting and getting text content from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            url = "https://example.com/article"
            content = b"<html><body>Article content</body></html>"
            final_url = "https://example.com/article"

            # Set cache entry
            success = cache.set(url, content, final_url, "text")
            assert success is True

            # Get cache entry
            cached = cache.get(url, "text")
            assert cached is not None
            assert cached["content"] == content
            assert cached["final_url"] == final_url
            assert cached["original_url"] == url

            cache.close()

    def test_cache_set_and_get_binary(self):
        """Test setting and getting binary content from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            url = "https://example.com/image.jpg"
            content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # PNG header
            final_url = "https://example.com/image.jpg"

            # Set cache entry
            success = cache.set(url, content, final_url, "binary")
            assert success is True

            # Get cache entry
            cached = cache.get(url, "binary")
            assert cached is not None
            assert cached["content"] == content
            assert cached["final_url"] == final_url

            cache.close()

    def test_cache_miss(self):
        """Test cache miss returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            cached = cache.get("https://example.com/notfound", "text")
            assert cached is None

            cache.close()

    def test_cache_different_content_types(self):
        """Test that text and binary caches are separate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            url = "https://example.com/resource"
            text_content = b"text content"
            binary_content = b"binary content"

            # Set both types
            cache.set(url, text_content, url, "text")
            cache.set(url, binary_content, url, "binary")

            # Get both types
            text_cached = cache.get(url, "text")
            binary_cached = cache.get(url, "binary")

            assert text_cached["content"] == text_content
            assert binary_cached["content"] == binary_content

            cache.close()

    def test_cache_clear(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # Add some entries
            cache.set("https://example.com/1", b"content1", "https://example.com/1", "text")
            cache.set("https://example.com/2", b"content2", "https://example.com/2", "text")

            # Verify they exist
            assert cache.get("https://example.com/1", "text") is not None
            assert cache.get("https://example.com/2", "text") is not None

            # Clear cache
            cache.clear()

            # Verify they're gone
            assert cache.get("https://example.com/1", "text") is None
            assert cache.get("https://example.com/2", "text") is None

            cache.close()

    def test_cache_stats(self):
        """Test getting cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # Add some entries
            cache.set("https://example.com/1", b"content1", "https://example.com/1", "text")
            cache.set("https://example.com/2", b"content2", "https://example.com/2", "text")

            stats = cache.get_stats()
            assert stats["entry_count"] == 2
            assert stats["size_bytes"] > 0
            assert stats["directory"] == str(cache.cache_dir)

            cache.close()


class TestCachedFetcher:
    """Test the CachedFetcher class."""

    @pytest.mark.asyncio
    async def test_cached_fetcher_caches_article_requests(self, httpserver):
        """Test that article requests are cached."""
        # Setup mock server
        content = "<html><body>Article content</body></html>"
        httpserver.expect_request("/article").respond_with_data(content, content_type="text/html")

        url = httpserver.url_for("/article")
        request_count = 0

        # Track requests
        def count_requests(request):
            nonlocal request_count
            request_count += 1

        httpserver.expect_request("/article").respond_with_data(
            content, content_type="text/html"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # First request should hit the network
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result1, final_url1 = await fetcher.fetch(url, context="article")

            # Verify content
            assert "Article content" in result1

            # Second request should hit the cache
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result2, final_url2 = await fetcher.fetch(url, context="article")

            # Verify cached content
            assert result1 == result2
            assert final_url1 == final_url2

            cache.close()

    @pytest.mark.asyncio
    async def test_cached_fetcher_does_not_cache_index_requests(self, httpserver):
        """Test that index requests are NOT cached."""
        # Setup mock server with counter
        request_count = 0

        def handle_request(request):
            nonlocal request_count
            request_count += 1
            return f"<html><body>Index request {request_count}</body></html>"

        httpserver.expect_request("/index").respond_with_handler(handle_request)

        url = httpserver.url_for("/index")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # First request
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result1, _ = await fetcher.fetch(url, context="index")

            # Second request should NOT use cache (should hit server again)
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result2, _ = await fetcher.fetch(url, context="index")

            # Results should be different (request count incremented)
            assert "Index request 1" in result1
            assert "Index request 2" in result2
            assert result1 != result2

            cache.close()

    @pytest.mark.asyncio
    async def test_cached_fetcher_caches_images(self, httpserver):
        """Test that image requests are cached."""
        # Setup mock server
        image_data = b"\x89PNG\r\n\x1a\n"  # PNG header
        httpserver.expect_request("/image.png").respond_with_data(
            image_data, content_type="image/png"
        )

        url = httpserver.url_for("/image.png")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # First request
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result1, _ = await fetcher.fetch_binary(url, context="image")

            # Verify image was downloaded
            assert result1 == image_data

            # Check cache
            cached = cache.get(url, "binary")
            assert cached is not None
            assert cached["content"] == image_data

            cache.close()

    @pytest.mark.asyncio
    async def test_cached_fetcher_caches_cover(self, httpserver):
        """Test that cover requests are cached."""
        # Setup mock server
        image_data = b"\x89PNG\r\n\x1a\n"
        httpserver.expect_request("/cover.png").respond_with_data(
            image_data, content_type="image/png"
        )

        url = httpserver.url_for("/cover.png")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # First request
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result1, _ = await fetcher.fetch_binary(url, context="cover")

            # Check cache
            cached = cache.get(url, "binary")
            assert cached is not None
            assert cached["content"] == image_data

            cache.close()

    @pytest.mark.asyncio
    async def test_cached_fetcher_disabled(self, httpserver):
        """Test that fetcher works when caching is disabled."""
        # Setup mock server with counter
        request_count = 0

        def handle_request(request):
            nonlocal request_count
            request_count += 1
            return f"<html><body>Request {request_count}</body></html>"

        httpserver.expect_request("/article").respond_with_handler(handle_request)

        url = httpserver.url_for("/article")

        # With caching disabled
        async with CachedFetcher(cache_enabled=False) as fetcher:
            result1, _ = await fetcher.fetch(url, context="article")

        async with CachedFetcher(cache_enabled=False) as fetcher:
            result2, _ = await fetcher.fetch(url, context="article")

        # Both requests should hit the server
        assert "Request 1" in result1
        assert "Request 2" in result2
        assert request_count == 2

    @pytest.mark.asyncio
    async def test_cached_fetcher_preserves_final_url(self, httpserver):
        """Test that cached responses preserve the final URL after redirects."""
        # Setup mock server with redirect
        httpserver.expect_request("/redirect").respond_with_data(
            "", status=301, headers={"Location": httpserver.url_for("/final")}
        )
        httpserver.expect_request("/final").respond_with_data(
            "<html><body>Final content</body></html>", content_type="text/html"
        )

        url = httpserver.url_for("/redirect")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = HttpCache(cache_dir=Path(tmpdir) / "test_cache")

            # First request (follows redirect)
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result1, final_url1 = await fetcher.fetch(url, context="article")

            # Verify final URL is correct
            assert "/final" in final_url1

            # Second request (from cache)
            async with CachedFetcher(cache_enabled=True, cache=cache) as fetcher:
                result2, final_url2 = await fetcher.fetch(url, context="article")

            # Verify cached final URL matches
            assert final_url1 == final_url2

            cache.close()
