"""
Cached HTTP fetcher wrapper for Gensi.

Wraps the standard Fetcher with intelligent caching that excludes index pages.
"""

from typing import Optional, Literal

from .fetcher import Fetcher
from .cache import HttpCache, ContentType


FetchContext = Literal["cover", "index", "article", "image"]


class CachedFetcher:
    """
    Cached wrapper around Fetcher with context-aware caching.

    Caches all requests except those with context="index".
    Provides the same interface as Fetcher for drop-in replacement.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache: Optional[HttpCache] = None,
        impersonate: str = "chrome136",
    ):
        """
        Initialize cached fetcher.

        Args:
            cache_enabled: Whether to enable caching. If False, acts as pass-through.
            cache: HttpCache instance. If None and cache_enabled, creates default cache.
            impersonate: Browser to impersonate (passed to Fetcher)
        """
        self.cache_enabled = cache_enabled
        self.impersonate = impersonate
        self._fetcher: Optional[Fetcher] = None

        # Initialize cache if enabled
        if cache_enabled:
            self.cache = cache if cache is not None else HttpCache()
        else:
            self.cache = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Create and enter the underlying Fetcher
        self._fetcher = Fetcher(impersonate=self.impersonate)
        await self._fetcher.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Exit the underlying Fetcher
        if self._fetcher:
            await self._fetcher.__aexit__(exc_type, exc_val, exc_tb)

    def _should_cache(self, context: FetchContext) -> bool:
        """
        Determine if request should be cached based on context.

        Args:
            context: The request context

        Returns:
            True if should cache, False otherwise
        """
        # Never cache if caching is disabled
        if not self.cache_enabled or self.cache is None:
            return False

        # Never cache index pages
        if context == "index":
            return False

        # Cache everything else (cover, article, image)
        return True

    async def fetch(
        self, url: str, timeout: int = 30, context: FetchContext = "article"
    ) -> tuple[str, str]:
        """
        Fetch a URL and return the content, with caching.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds
            context: Request context for cache decision

        Returns:
            Tuple of (content, final_url) - content as text, final URL after redirects

        Raises:
            Exception: If the fetch fails
        """
        if not self._fetcher:
            raise RuntimeError("CachedFetcher must be used as async context manager")

        # Check cache if caching is enabled for this context
        if self._should_cache(context):
            cached = self.cache.get(url, "text")
            if cached is not None:
                # Cache hit - return cached content
                content_bytes = cached["content"]
                final_url = cached["final_url"]
                # Convert bytes back to string
                content = content_bytes.decode('utf-8')
                return content, final_url

        # Cache miss or caching disabled - fetch from network
        try:
            content, final_url = await self._fetcher.fetch(url, timeout)

            # Store in cache if caching is enabled for this context
            if self._should_cache(context):
                content_bytes = content.encode('utf-8')
                self.cache.set(url, content_bytes, final_url, "text")

            return content, final_url

        except Exception as e:
            # On fetch error, just re-raise (don't try cache fallback)
            raise

    async def fetch_binary(
        self, url: str, timeout: int = 30, context: FetchContext = "image"
    ) -> tuple[bytes, str]:
        """
        Fetch a URL and return binary content, with caching.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds
            context: Request context for cache decision

        Returns:
            Tuple of (content, final_url) - content as bytes, final URL after redirects

        Raises:
            Exception: If the fetch fails
        """
        if not self._fetcher:
            raise RuntimeError("CachedFetcher must be used as async context manager")

        # Check cache if caching is enabled for this context
        if self._should_cache(context):
            cached = self.cache.get(url, "binary")
            if cached is not None:
                # Cache hit - return cached content
                content = cached["content"]
                final_url = cached["final_url"]
                return content, final_url

        # Cache miss or caching disabled - fetch from network
        try:
            content, final_url = await self._fetcher.fetch_binary(url, timeout)

            # Store in cache if caching is enabled for this context
            if self._should_cache(context):
                self.cache.set(url, content, final_url, "binary")

            return content, final_url

        except Exception as e:
            # On fetch error, just re-raise (don't try cache fallback)
            raise
