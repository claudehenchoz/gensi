"""
HTTP response caching for Gensi.

Provides disk-based caching with TTL support for HTTP requests.
Cache is stored in system-appropriate cache directory.
"""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal

import diskcache
from platformdirs import user_cache_dir


ContentType = Literal["text", "binary"]


class HttpCache:
    """
    Disk-based HTTP response cache with TTL support.

    Stores responses in system cache directory with configurable TTL.
    Thread-safe and async-safe through diskcache's locking mechanism.
    """

    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize HTTP cache.

        Args:
            cache_dir: Directory for cache storage. If None, uses system cache directory.
            ttl_seconds: Time-to-live for cached entries in seconds. Default: 7 days.
        """
        if cache_dir is None:
            cache_dir = Path(user_cache_dir("gensi", "gensi")) / "http_cache"

        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize diskcache Cache
        self.cache = diskcache.Cache(str(self.cache_dir))

    def _make_cache_key(self, url: str, content_type: ContentType) -> str:
        """
        Generate cache key from URL and content type.

        Args:
            url: The request URL
            content_type: Either "text" or "binary"

        Returns:
            Cache key string
        """
        # Use SHA256 hash of URL to keep keys consistent length and filesystem-safe
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        return f"{url_hash}_{content_type}"

    def get(self, url: str, content_type: ContentType) -> Optional[dict]:
        """
        Retrieve cached response for URL.

        Args:
            url: The request URL
            content_type: Either "text" or "binary"

        Returns:
            Dict with keys: content (bytes), final_url (str), cached_at (datetime), original_url (str)
            Returns None if not in cache or expired.
        """
        cache_key = self._make_cache_key(url, content_type)

        try:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
        except Exception:
            # On any cache error, return None (cache miss)
            pass

        return None

    def set(self, url: str, content: bytes, final_url: str, content_type: ContentType) -> bool:
        """
        Store response in cache.

        Args:
            url: The original request URL
            content: Response content as bytes
            final_url: Final URL after redirects
            content_type: Either "text" or "binary"

        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self._make_cache_key(url, content_type)

        cache_entry = {
            "content": content,
            "final_url": final_url,
            "cached_at": datetime.now(),
            "original_url": url,
        }

        try:
            # Set with TTL - diskcache will automatically expire after ttl_seconds
            self.cache.set(cache_key, cache_entry, expire=self.ttl_seconds)
            return True
        except Exception:
            # On any cache error, return False but don't raise
            return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with keys: size_bytes, entry_count, directory
        """
        return {
            "size_bytes": self.cache.volume(),
            "entry_count": len(self.cache),
            "directory": str(self.cache_dir),
        }

    def close(self) -> None:
        """Close cache and release resources."""
        self.cache.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
