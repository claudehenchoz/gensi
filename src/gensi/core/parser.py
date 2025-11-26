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
        num_indices = len(self.data['index'])
        for i, index in enumerate(self.data['index']):
            # 'name' is only required if there are multiple indices
            if num_indices > 1:
                if 'name' not in index or not index['name'].strip():
                    raise ValueError(f"Index {i}: 'name' is required when there are multiple [[index]] sections")

            if 'url' not in index:
                raise ValueError(f"Index {i}: 'url' is required")
            if 'type' not in index:
                raise ValueError(f"Index {i}: 'type' is required")
            if index['type'] not in ['html', 'rss', 'json', 'bluesky']:
                raise ValueError(f"Index {i}: 'type' must be 'html', 'rss', 'json', or 'bluesky'")

            # Validate HTML index
            if index['type'] == 'html':
                # Check if using Python override or simple mode
                if 'python' not in index:
                    if 'links' not in index:
                        raise ValueError(f"Index {i}: 'links' is required for HTML type (CSS selector pointing to <a> elements)")

                # If response_type is json, validate json_path
                if index.get('response_type') == 'json':
                    if 'python' not in index and 'json_path' not in index:
                        raise ValueError(f"Index {i}: 'json_path' is required when response_type='json' in simple mode")

            # Validate JSON index
            elif index['type'] == 'json':
                # JSON indices require either json_path+links or python override
                if 'python' not in index:
                    if 'json_path' not in index:
                        raise ValueError(f"Index {i}: 'json_path' is required for JSON type in simple mode")
                    if 'links' not in index:
                        raise ValueError(f"Index {i}: 'links' is required for JSON type in simple mode (CSS selector for HTML extracted from JSON)")

            # Validate Bluesky index
            elif index['type'] == 'bluesky':
                if 'python' not in index and 'username' not in index:
                    raise ValueError(f"Index {i}: 'username' is required for Bluesky type in simple mode")

                if 'limit' in index:
                    limit = index['limit']
                    if not isinstance(limit, int) or limit < 1 or limit > 100:
                        raise ValueError(f"Index {i}: 'limit' must be an integer between 1 and 100")

            # Validate url_transform section if present
            if 'url_transform' in index:
                transform = index['url_transform']
                if not isinstance(transform, dict):
                    raise ValueError(f"Index {i}: 'url_transform' must be a section")

                # Check if using Python override or simple mode
                has_python = 'python' in transform
                has_pattern = 'pattern' in transform
                has_template = 'template' in transform

                if has_python:
                    # Python mode: only python subsection is needed
                    if has_pattern or has_template:
                        raise ValueError(f"Index {i}: url_transform cannot have both 'python' and 'pattern'/'template'")
                else:
                    # Simple mode: both pattern and template are required
                    if not has_pattern:
                        raise ValueError(f"Index {i}: url_transform requires 'pattern' in simple mode")
                    if not has_template:
                        raise ValueError(f"Index {i}: url_transform requires 'template' in simple mode")

        # Validate cover section if present
        if 'cover' in self.data:
            if 'url' not in self.data['cover']:
                raise ValueError("Cover: 'url' is required")

        # Validate article section if present
        if 'article' in self.data:
            article = self.data['article']

            # Validate response_type if present
            if 'response_type' in article:
                if article['response_type'] not in ['html', 'json']:
                    raise ValueError("Article: 'response_type' must be 'html' or 'json'")

                # If response_type is json, validate json_path
                if article['response_type'] == 'json':
                    if 'python' not in article and 'json_path' not in article:
                        raise ValueError("Article: 'json_path' is required when response_type='json' in simple mode")

                    # Validate json_path format (can be string or dict)
                    if 'json_path' in article:
                        json_path = article['json_path']
                        if isinstance(json_path, dict):
                            # Dict mode: must have 'content' key, optional title/author/date
                            if 'content' not in json_path:
                                raise ValueError("Article: json_path dict must have 'content' key")
                            # All values must be strings
                            for key, value in json_path.items():
                                if not isinstance(value, str):
                                    raise ValueError(f"Article: json_path['{key}'] must be a string")
                        elif not isinstance(json_path, str):
                            raise ValueError("Article: 'json_path' must be a string or dict")

            # Check if using Python override or simple mode
            # Note: if response_type='json' with json_path, content selector is not needed
            # (content will be extracted from JSON)
            if 'python' not in article:
                is_json_mode = article.get('response_type') == 'json' and 'json_path' in article
                if not is_json_mode and 'content' not in article:
                    raise ValueError("Article: 'content' selector is required in simple mode")

        # Validate replacements section if present
        if 'replacements' in self.data:
            replacements = self.data['replacements']
            if not isinstance(replacements, list):
                raise ValueError("'replacements' must be a list of [[replacements]] sections")

            for i, replacement in enumerate(replacements):
                if 'pattern' not in replacement:
                    raise ValueError(f"Replacement {i}: 'pattern' is required")
                if 'replacement' not in replacement:
                    raise ValueError(f"Replacement {i}: 'replacement' is required")
                if 'regex' not in replacement:
                    raise ValueError(f"Replacement {i}: 'regex' is required (must be true or false)")

                # Validate types
                if not isinstance(replacement['pattern'], str):
                    raise ValueError(f"Replacement {i}: 'pattern' must be a string")
                if not isinstance(replacement['replacement'], str):
                    raise ValueError(f"Replacement {i}: 'replacement' must be a string")
                if not isinstance(replacement['regex'], bool):
                    raise ValueError(f"Replacement {i}: 'regex' must be a boolean (true or false)")

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

    @property
    def replacements(self) -> list[dict[str, Any]]:
        """Get the list of replacement configurations."""
        return self.data.get('replacements', [])
