"""Tests for HTTP fetcher."""

import pytest
from gensi.core.fetcher import Fetcher


@pytest.mark.asyncio
class TestFetcher:
    """Test HTTP fetcher functionality."""

    async def test_fetch_html(self, httpserver_with_content):
        """Test fetching HTML content."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            content, final_url = await fetcher.fetch(httpserver.url_for('/blog_index.html'))

        assert "Blog Archive" in content
        assert final_url is not None

    async def test_fetch_binary(self, httpserver_with_content):
        """Test fetching binary content (images)."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            data, final_url = await fetcher.fetch_binary(httpserver.url_for('/images/cover.jpg'))

        assert isinstance(data, bytes)
        assert len(data) > 0
        assert final_url is not None

    async def test_fetch_multiple_requests(self, httpserver_with_content):
        """Test making multiple fetch requests."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            content1, _ = await fetcher.fetch(httpserver.url_for('/article1.html'))
            content2, _ = await fetcher.fetch(httpserver.url_for('/article2.html'))

        assert "First Article" in content1
        assert "Second Article" in content2

    async def test_fetch_rss_feed(self, httpserver_with_content):
        """Test fetching RSS feed."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            content, final_url = await fetcher.fetch(httpserver.url_for('/test_feed_rss.xml'))

        assert "<?xml" in content
        assert "Test Blog" in content
        assert "<rss" in content

    async def test_fetch_atom_feed(self, httpserver_with_content):
        """Test fetching Atom feed."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            content, final_url = await fetcher.fetch(httpserver.url_for('/test_feed_atom.xml'))

        assert "<?xml" in content
        assert "Atom" in content

    async def test_fetch_returns_final_url(self, httpserver_with_content):
        """Test that fetch returns the final URL after redirects."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            _, final_url = await fetcher.fetch(httpserver.url_for('/article1.html'))

        assert final_url is not None
        assert 'article1.html' in final_url

    async def test_fetch_context_manager(self, httpserver_with_content):
        """Test using fetcher as context manager."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            assert fetcher is not None
            content, _ = await fetcher.fetch(httpserver.url_for('/blog_index.html'))
            assert len(content) > 0

        # After exiting context, session should be closed

    async def test_fetch_different_content_types(self, httpserver_with_content):
        """Test fetching different content types."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            # HTML
            html, _ = await fetcher.fetch(httpserver.url_for('/article1.html'))
            assert '<html' in html.lower()

            # XML/RSS
            xml, _ = await fetcher.fetch(httpserver.url_for('/test_feed_rss.xml'))
            assert '<?xml' in xml

            # Image
            img, _ = await fetcher.fetch_binary(httpserver.url_for('/images/test1.jpg'))
            assert isinstance(img, bytes)

    async def test_fetch_404_error(self, httpserver):
        """Test fetching non-existent resource."""
        httpserver.expect_request('/nonexistent.html').respond_with_data(
            'Not Found', status=404
        )

        async with Fetcher() as fetcher:
            with pytest.raises(Exception):
                await fetcher.fetch(httpserver.url_for('/nonexistent.html'))

    async def test_fetch_multiple_images(self, httpserver_with_content):
        """Test fetching multiple images."""
        httpserver = httpserver_with_content

        async with Fetcher() as fetcher:
            img1, _ = await fetcher.fetch_binary(httpserver.url_for('/images/test1.jpg'))
            img2, _ = await fetcher.fetch_binary(httpserver.url_for('/images/test2.png'))

        assert isinstance(img1, bytes)
        assert isinstance(img2, bytes)
        assert len(img1) > 0
        assert len(img2) > 0
