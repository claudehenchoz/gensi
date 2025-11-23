"""Apply search/replace transformations to HTML content."""

import re
from typing import Any


def apply_replacements(content: str, replacements: list[dict[str, Any]]) -> str:
    """
    Apply a list of search/replace transformations to HTML content.

    Replacements are applied in the order they are defined in the list.
    Each replacement can be either a literal string replacement or a regex replacement.

    Args:
        content: The HTML content to transform
        replacements: List of replacement configurations, each with:
            - pattern (str): The pattern to search for
            - replacement (str): The replacement text
            - regex (bool): Whether to use regex matching

    Returns:
        The transformed HTML content

    Example:
        >>> replacements = [
        ...     {"pattern": '<p class="center">• • • •</p>', "replacement": "<hr/>", "regex": False},
        ...     {"pattern": r'<p class="center">[•\s]+</p>', "replacement": "<hr/>", "regex": True},
        ... ]
        >>> apply_replacements(content, replacements)
    """
    if not replacements:
        return content

    result = content

    for replacement_config in replacements:
        pattern = replacement_config['pattern']
        replacement = replacement_config['replacement']
        is_regex = replacement_config['regex']

        if is_regex:
            # Use regex replacement
            try:
                result = re.sub(pattern, replacement, result)
            except re.error as e:
                # If the regex is invalid, skip this replacement and log warning
                # (In a production system, this should be logged properly)
                print(f"Warning: Invalid regex pattern '{pattern}': {e}")
                continue
        else:
            # Use literal string replacement
            result = result.replace(pattern, replacement)

    return result
