"""
Tests for JSON path extraction utilities.
"""

import pytest
from gensi.core.json_utils import extract_json_path, extract_json_paths, extract_json_paths_as_list, JSONExtractionError


class TestExtractJsonPath:
    """Tests for extract_json_path function."""

    def test_extract_simple_path_from_dict(self):
        """Test extracting a simple path from a parsed dict."""
        data = {"data": {"magazin": {"content": "<html>Test content</html>"}}}
        result = extract_json_path(data, "data.magazin.content")
        assert result == "<html>Test content</html>"

    def test_extract_simple_path_from_string(self):
        """Test extracting a simple path from a JSON string."""
        json_str = '{"data": {"magazin": {"content": "<html>Test</html>"}}}'
        result = extract_json_path(json_str, "data.magazin.content")
        assert result == "<html>Test</html>"

    def test_extract_with_dollar_prefix(self):
        """Test extraction with explicit $ prefix in path."""
        data = {"data": {"value": "test"}}
        result = extract_json_path(data, "$.data.value")
        assert result == "test"

    def test_extract_array_element(self):
        """Test extracting from an array."""
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        result = extract_json_path(data, "items[0].name")
        assert result == "first"

    def test_extract_nested_object(self):
        """Test extracting deeply nested values."""
        data = {
            "response": {"data": {"reportage": {"title": "Article Title", "content": "<p>Text</p>"}}}
        }
        result = extract_json_path(data, "response.data.reportage.title")
        assert result == "Article Title"

    def test_extract_number(self):
        """Test extracting numeric values."""
        data = {"count": 42}
        result = extract_json_path(data, "count")
        assert result == 42

    def test_extract_boolean(self):
        """Test extracting boolean values."""
        data = {"enabled": True}
        result = extract_json_path(data, "enabled")
        assert result is True

    def test_extract_null(self):
        """Test extracting null values."""
        data = {"value": None}
        result = extract_json_path(data, "value")
        assert result is None

    def test_nonexistent_path_raises_error(self):
        """Test that nonexistent paths raise JSONExtractionError."""
        data = {"data": {"value": "test"}}
        with pytest.raises(JSONExtractionError, match="did not match any values"):
            extract_json_path(data, "nonexistent.path")

    def test_invalid_json_string_raises_error(self):
        """Test that invalid JSON strings raise JSONExtractionError."""
        with pytest.raises(JSONExtractionError, match="Failed to parse JSON"):
            extract_json_path("not valid json", "some.path")

    def test_invalid_jsonpath_expression_raises_error(self):
        """Test that invalid JSONPath expressions raise JSONExtractionError."""
        data = {"value": "test"}
        with pytest.raises(JSONExtractionError, match="Failed to parse JSONPath expression"):
            extract_json_path(data, "$.[[[invalid")

    def test_multiple_matches_returns_first(self):
        """Test that when multiple values match, the first is returned."""
        data = {"items": [{"value": "first"}, {"value": "second"}]}
        # This path matches all 'value' fields in items array
        result = extract_json_path(data, "items[*].value")
        assert result == "first"


class TestExtractJsonPaths:
    """Tests for extract_json_paths function (multiple path extraction)."""

    def test_extract_multiple_paths_from_dict(self):
        """Test extracting multiple paths from a dict."""
        data = {
            "data": {
                "reportage": {
                    "title": "Article Title",
                    "content": "<p>Content</p>",
                    "author": "John Doe",
                }
            }
        }
        paths = {
            "title": "data.reportage.title",
            "content": "data.reportage.content",
            "author": "data.reportage.author",
        }
        result = extract_json_paths(data, paths)
        assert result == {
            "title": "Article Title",
            "content": "<p>Content</p>",
            "author": "John Doe",
        }

    def test_extract_multiple_paths_from_string(self):
        """Test extracting multiple paths from a JSON string."""
        json_str = '{"data": {"title": "Test", "content": "<p>Text</p>"}}'
        paths = {"title": "data.title", "content": "data.content"}
        result = extract_json_paths(json_str, paths)
        assert result == {"title": "Test", "content": "<p>Text</p>"}

    def test_extract_with_missing_optional_path(self):
        """Test that missing paths raise errors (no optional paths in current design)."""
        data = {"data": {"title": "Test"}}
        paths = {"title": "data.title", "missing": "data.nonexistent"}
        with pytest.raises(JSONExtractionError, match="Failed to extract 'missing'"):
            extract_json_paths(data, paths)

    def test_extract_empty_paths_dict(self):
        """Test extracting with empty paths dict returns empty result."""
        data = {"data": "value"}
        result = extract_json_paths(data, {})
        assert result == {}

    def test_invalid_json_in_multiple_extraction(self):
        """Test that invalid JSON raises error in multiple extraction."""
        with pytest.raises(JSONExtractionError, match="Failed to parse JSON"):
            extract_json_paths("invalid json", {"field": "path"})


class TestExtractJsonPathsAsList:
    """Tests for extract_json_paths_as_list function (array extraction)."""

    def test_extract_simple_array_from_dict(self):
        """Test extracting all URLs from JSON array."""
        data = {
            "results": [
                {"url": "https://example.com/1"},
                {"url": "https://example.com/2"},
                {"url": "https://example.com/3"}
            ]
        }
        result = extract_json_paths_as_list(data, "results[*].url")
        assert len(result) == 3
        assert result == [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]

    def test_extract_array_from_json_string(self):
        """Test extracting array from JSON string."""
        json_str = '{"items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}'
        result = extract_json_paths_as_list(json_str, "items[*].id")
        assert result == ["a", "b", "c"]

    def test_extract_nested_object_arrays(self):
        """Test extracting from nested object arrays."""
        data = {
            "data": {
                "items": [
                    {"link": {"href": "/page1"}},
                    {"link": {"href": "/page2"}},
                    {"link": {"href": "/page3"}}
                ]
            }
        }
        result = extract_json_paths_as_list(data, "data.items[*].link.href")
        assert result == ["/page1", "/page2", "/page3"]

    def test_extract_with_dollar_prefix(self):
        """Test with explicit $ prefix."""
        data = {"items": [{"id": "1"}, {"id": "2"}]}
        result = extract_json_paths_as_list(data, "$.items[*].id")
        assert result == ["1", "2"]

    def test_extract_mixed_types_in_array(self):
        """Test extracting array with mixed types."""
        data = {"values": [{"val": 1}, {"val": "string"}, {"val": True}, {"val": None}]}
        result = extract_json_paths_as_list(data, "values[*].val")
        assert result == [1, "string", True, None]

    def test_extract_single_element_returns_list(self):
        """Test that single element is still returned as list."""
        data = {"items": [{"url": "https://example.com"}]}
        result = extract_json_paths_as_list(data, "items[*].url")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "https://example.com"

    def test_empty_array_raises_error(self):
        """Test that empty array raises JSONExtractionError."""
        data = {"results": []}
        with pytest.raises(JSONExtractionError, match="did not match any values"):
            extract_json_paths_as_list(data, "results[*].url")

    def test_nonexistent_path_raises_error(self):
        """Test that nonexistent paths raise JSONExtractionError."""
        data = {"data": {"value": "test"}}
        with pytest.raises(JSONExtractionError, match="did not match any values"):
            extract_json_paths_as_list(data, "nonexistent[*].path")

    def test_invalid_json_string_raises_error(self):
        """Test that invalid JSON strings raise JSONExtractionError."""
        with pytest.raises(JSONExtractionError, match="Failed to parse JSON"):
            extract_json_paths_as_list("not valid json", "some[*].path")

    def test_invalid_jsonpath_expression_raises_error(self):
        """Test that invalid JSONPath expressions raise JSONExtractionError."""
        data = {"value": "test"}
        with pytest.raises(JSONExtractionError, match="Failed to parse JSONPath expression"):
            extract_json_paths_as_list(data, "$.[[[invalid")

    def test_lux_magazine_structure(self):
        """Test extracting URLs from Lux Magazine API structure."""
        json_response = {
            "results": [
                {
                    "id": 9641,
                    "title": "No Lesbians",
                    "permalink": "https://lux-magazine.com/article/queer-immigration/",
                    "date": {"formatted": "July 11, 2025"}
                },
                {
                    "id": 9642,
                    "title": "Another Article",
                    "permalink": "https://lux-magazine.com/article/another-article/",
                    "date": {"formatted": "July 12, 2025"}
                }
            ]
        }
        result = extract_json_paths_as_list(json_response, "results[*].permalink")
        assert len(result) == 2
        assert result[0] == "https://lux-magazine.com/article/queer-immigration/"
        assert result[1] == "https://lux-magazine.com/article/another-article/"

    def test_direct_array_without_wildcard(self):
        """Test extracting direct array values."""
        data = {"urls": ["https://a.com", "https://b.com", "https://c.com"]}
        result = extract_json_paths_as_list(data, "urls[*]")
        assert result == ["https://a.com", "https://b.com", "https://c.com"]


class TestRealWorldExamples:
    """Tests using real-world JSON structures from GraphQL APIs."""

    def test_reportagen_magazine_structure(self):
        """Test extracting from Reportagen magazine API structure."""
        json_response = {
            "data": {
                "magazin": {
                    "content": '<div class="block-reportage-teaser"><a href="/reportage/test/">Link</a></div>'
                }
            }
        }
        result = extract_json_path(json_response, "data.magazin.content")
        assert "<div" in result
        assert "/reportage/test/" in result

    def test_reportagen_article_structure(self):
        """Test extracting from Reportagen article API structure."""
        json_response = {
            "data": {
                "reportage": {
                    "title": "Article Title",
                    "content": "<article><p>Article content here</p></article>",
                }
            }
        }
        paths = {"title": "data.reportage.title", "content": "data.reportage.content"}
        result = extract_json_paths(json_response, paths)
        assert result["title"] == "Article Title"
        assert "<article>" in result["content"]

    def test_graphql_with_null_values(self):
        """Test handling GraphQL responses with null values."""
        json_response = {"data": {"article": {"title": "Test", "author": None, "content": "<p>Text</p>"}}}
        paths = {"title": "data.article.title", "author": "data.article.author"}
        result = extract_json_paths(json_response, paths)
        assert result["title"] == "Test"
        assert result["author"] is None
