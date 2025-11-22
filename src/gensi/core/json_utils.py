"""
Utilities for JSON parsing and extraction using JSONPath expressions.
"""

import json
from typing import Any, Union
from jsonpath_ng import parse as jsonpath_parse


class JSONExtractionError(Exception):
    """Raised when JSON extraction fails."""

    pass


def extract_json_path(json_data: Union[str, dict], path: str) -> Any:
    """
    Extract a value from JSON data using a JSONPath expression.

    Args:
        json_data: Either a JSON string or a parsed dict/list
        path: JSONPath expression (e.g., "data.magazin.content", "$.items[0].title")

    Returns:
        The extracted value. If multiple matches found, returns the first one.

    Raises:
        JSONExtractionError: If JSON parsing fails or path doesn't match anything
    """
    # Parse JSON string if needed
    if isinstance(json_data, str):
        try:
            parsed_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise JSONExtractionError(f"Failed to parse JSON: {e}")
    else:
        parsed_data = json_data

    # Normalize path (add $ prefix if not present)
    if not path.startswith("$"):
        # Convert dot notation to JSONPath notation
        # "data.magazin.content" -> "$.data.magazin.content"
        path = f"$.{path}"

    # Parse and execute JSONPath expression
    try:
        jsonpath_expr = jsonpath_parse(path)
        matches = jsonpath_expr.find(parsed_data)
    except Exception as e:
        raise JSONExtractionError(f"Failed to parse JSONPath expression '{path}': {e}")

    if not matches:
        raise JSONExtractionError(f"JSONPath '{path}' did not match any values in the JSON data")

    # Return the first match value
    return matches[0].value


def extract_json_paths(json_data: Union[str, dict], paths: dict[str, str]) -> dict[str, Any]:
    """
    Extract multiple values from JSON data using a dict of JSONPath expressions.

    Args:
        json_data: Either a JSON string or a parsed dict/list
        paths: Dict mapping field names to JSONPath expressions
               Example: {"content": "data.reportage.content", "title": "data.reportage.title"}

    Returns:
        Dict mapping field names to extracted values

    Raises:
        JSONExtractionError: If JSON parsing fails or any required path doesn't match
    """
    # Parse JSON string once if needed
    if isinstance(json_data, str):
        try:
            parsed_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise JSONExtractionError(f"Failed to parse JSON: {e}")
    else:
        parsed_data = json_data

    results = {}
    for field_name, path in paths.items():
        try:
            results[field_name] = extract_json_path(parsed_data, path)
        except JSONExtractionError as e:
            # Re-raise with more context about which field failed
            raise JSONExtractionError(f"Failed to extract '{field_name}': {e}")

    return results
