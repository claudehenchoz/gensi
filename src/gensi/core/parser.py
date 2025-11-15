"""Parser for .gensi TOML recipe files."""

import tomllib
from pathlib import Path
from typing import Any


class GensiParser:
    """Parser for .gensi TOML recipe files."""

    def __init__(self, filepath: Path | str):
        """
        Initialize the parser with a .gensi file path.

        Args:
            filepath: Path to the .gensi file
        """
        self.filepath = Path(filepath)
        self.data: dict[str, Any] = {}
        self._parse()

    def _parse(self) -> None:
        """Parse the .gensi TOML file."""
        with open(self.filepath, 'rb') as f:
            self.data = tomllib.load(f)

        # Validate required fields
        self._validate()

    def _validate(self) -> None:
        """Validate the parsed .gensi data."""
        # Title is required
        if 'title' not in self.data or not self.data['title'].strip():
            raise ValueError("'title' is required and must be non-empty")

        # At least one index is required
        if 'index' not in self.data or not self.data['index']:
            raise ValueError("At least one [[index]] section is required")

        # Validate each index
        for i, index in enumerate(self.data['index']):
            if 'name' not in index or not index['name'].strip():
                raise ValueError(f"Index {i}: 'name' is required and must be non-empty")
            if 'url' not in index:
                raise ValueError(f"Index {i}: 'url' is required")
            if 'type' not in index:
                raise ValueError(f"Index {i}: 'type' is required")
            if index['type'] not in ['html', 'rss']:
                raise ValueError(f"Index {i}: 'type' must be 'html' or 'rss'")

            # Validate HTML index
            if index['type'] == 'html':
                # Check if using Python override or simple mode
                if 'python' not in index:
                    if 'items' not in index:
                        raise ValueError(f"Index {i}: 'items' is required for HTML type")
                    if 'link' not in index:
                        raise ValueError(f"Index {i}: 'link' is required for HTML type")

        # Validate cover section if present
        if 'cover' in self.data:
            if 'url' not in self.data['cover']:
                raise ValueError("Cover: 'url' is required")

        # Validate article section if present
        if 'article' in self.data:
            # Check if using Python override or simple mode
            if 'python' not in self.data['article']:
                if 'content' not in self.data['article']:
                    raise ValueError("Article: 'content' selector is required in simple mode")

    @property
    def title(self) -> str:
        """Get the EPUB title."""
        return self.data['title']

    @property
    def author(self) -> str | None:
        """Get the EPUB author."""
        return self.data.get('author')

    @property
    def language(self) -> str | None:
        """Get the EPUB language."""
        return self.data.get('language')

    @property
    def cover(self) -> dict[str, Any] | None:
        """Get the cover configuration."""
        return self.data.get('cover')

    @property
    def indices(self) -> list[dict[str, Any]]:
        """Get the list of index configurations."""
        return self.data.get('index', [])

    @property
    def article(self) -> dict[str, Any] | None:
        """Get the global article configuration."""
        return self.data.get('article')

    def get_article_config(self, index_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Get the article configuration for a specific index.

        Returns the per-index article config if present, otherwise the global config.

        Args:
            index_data: The index configuration dictionary

        Returns:
            The article configuration to use, or None
        """
        return index_data.get('article', self.article)
