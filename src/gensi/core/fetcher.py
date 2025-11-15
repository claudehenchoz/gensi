"""Web content fetcher using curl_cffi with chrome136 impersonation."""

import asyncio
from typing import Optional
from curl_cffi import requests
from curl_cffi.requests import AsyncSession


class Fetcher:
    """Fetches web content using curl_cffi with chrome136 impersonation."""

    def __init__(self, impersonate: str = "chrome136"):
        """
        Initialize the fetcher.

        Args:
            impersonate: Browser to impersonate (default: chrome136)
        """
        self.impersonate = impersonate
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = AsyncSession(impersonate=self.impersonate)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    async def fetch(self, url: str, timeout: int = 30) -> tuple[str, str]:
        """
        Fetch a URL and return the content.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Tuple of (content, final_url) - content as text, final URL after redirects

        Raises:
            Exception: If the fetch fails
        """
        if not self._session:
            raise RuntimeError("Fetcher must be used as async context manager")

        try:
            response = await self._session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text, str(response.url)
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}") from e

    async def fetch_binary(self, url: str, timeout: int = 30) -> tuple[bytes, str]:
        """
        Fetch a URL and return binary content.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Tuple of (content, final_url) - content as bytes, final URL after redirects

        Raises:
            Exception: If the fetch fails
        """
        if not self._session:
            raise RuntimeError("Fetcher must be used as async context manager")

        try:
            response = await self._session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.content, str(response.url)
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}") from e


def fetch_sync(url: str, timeout: int = 30, impersonate: str = "chrome136") -> tuple[str, str]:
    """
    Synchronously fetch a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        impersonate: Browser to impersonate

    Returns:
        Tuple of (content, final_url) - content as text, final URL after redirects

    Raises:
        Exception: If the fetch fails
    """
    try:
        response = requests.get(url, timeout=timeout, impersonate=impersonate, allow_redirects=True)
        response.raise_for_status()
        return response.text, str(response.url)
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}") from e


def fetch_binary_sync(url: str, timeout: int = 30, impersonate: str = "chrome136") -> tuple[bytes, str]:
    """
    Synchronously fetch binary content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        impersonate: Browser to impersonate

    Returns:
        Tuple of (content, final_url) - content as bytes, final URL after redirects

    Raises:
        Exception: If the fetch fails
    """
    try:
        response = requests.get(url, timeout=timeout, impersonate=impersonate, allow_redirects=True)
        response.raise_for_status()
        return response.content, str(response.url)
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}") from e
