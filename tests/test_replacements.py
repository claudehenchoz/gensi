"""Tests for search/replace transformations."""

import pytest
from gensi.core.replacements import apply_replacements


class TestReplacements:
    """Test replacement functionality."""

    def test_no_replacements(self):
        """Test that content is unchanged when no replacements are provided."""
        content = "<p>This is a test.</p>"
        result = apply_replacements(content, [])
        assert result == content

    def test_literal_replacement(self):
        """Test literal string replacement."""
        content = '<p class="center">• • • •</p>'
        replacements = [
            {
                "pattern": '<p class="center">• • • •</p>',
                "replacement": "<hr/>",
                "regex": False
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == "<hr/>"

    def test_regex_replacement_simple(self):
        """Test simple regex replacement."""
        content = '<p class="center">• • •</p><p class="center">•   •</p>'
        replacements = [
            {
                "pattern": r'<p class="center">[•\s]+</p>',
                "replacement": "<hr/>",
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == "<hr/><hr/>"

    def test_regex_replacement_with_groups(self):
        """Test regex replacement with capture groups."""
        content = '<div class="article"><p>Content here</p></div>'
        replacements = [
            {
                "pattern": r'<div class="(\w+)">(.*?)</div>',
                "replacement": r'<section class="\1">\2</section>',
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == '<section class="article"><p>Content here</p></section>'

    def test_multiple_replacements(self):
        """Test applying multiple replacements in order."""
        content = '<p class="center">• • • •</p><div class="foo">Test</div>'
        replacements = [
            {
                "pattern": '<p class="center">• • • •</p>',
                "replacement": "<hr/>",
                "regex": False
            },
            {
                "pattern": r'<div class="(\w+)">(.*?)</div>',
                "replacement": r'<section class="\1">\2</section>',
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == '<hr/><section class="foo">Test</section>'

    def test_replacement_order_matters(self):
        """Test that replacements are applied in order."""
        content = "<p>foo</p>"
        replacements = [
            {"pattern": "foo", "replacement": "bar", "regex": False},
            {"pattern": "bar", "replacement": "baz", "regex": False}
        ]
        result = apply_replacements(content, replacements)
        # First replacement changes foo to bar, second changes bar to baz
        assert result == "<p>baz</p>"

    def test_literal_replacement_special_chars(self):
        """Test literal replacement with regex special characters."""
        content = "<p>Price: $10.00</p>"
        replacements = [
            {
                "pattern": "$10.00",
                "replacement": "$20.00",
                "regex": False
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == "<p>Price: $20.00</p>"

    def test_regex_replacement_special_chars(self):
        """Test regex replacement with proper escaping."""
        content = "<p>Price: $10.00</p>"
        replacements = [
            {
                "pattern": r"\$\d+\.\d+",
                "replacement": "FREE",
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == "<p>Price: FREE</p>"

    def test_no_match_literal(self):
        """Test literal replacement when pattern doesn't match."""
        content = "<p>This is a test.</p>"
        replacements = [
            {
                "pattern": "foo",
                "replacement": "bar",
                "regex": False
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == content

    def test_no_match_regex(self):
        """Test regex replacement when pattern doesn't match."""
        content = "<p>This is a test.</p>"
        replacements = [
            {
                "pattern": r"foo\d+",
                "replacement": "bar",
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == content

    def test_invalid_regex_handled(self, capsys):
        """Test that invalid regex patterns are handled gracefully."""
        content = "<p>This is a test.</p>"
        replacements = [
            {
                "pattern": "[invalid(regex",
                "replacement": "bar",
                "regex": True
            }
        ]
        result = apply_replacements(content, replacements)
        # Content should be unchanged
        assert result == content
        # Should print a warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "warning" in captured.out.lower()

    def test_empty_content(self):
        """Test replacement on empty content."""
        content = ""
        replacements = [
            {
                "pattern": "foo",
                "replacement": "bar",
                "regex": False
            }
        ]
        result = apply_replacements(content, replacements)
        assert result == ""

    def test_complex_html_content(self):
        """Test replacements on complex HTML content."""
        content = """
<article>
    <h1>Title</h1>
    <p class="center">* * * *</p>
    <div class="footer">Footer text</div>
</article>
"""
        replacements = [
            {
                "pattern": r'<p class="center">[*\s]+</p>',
                "replacement": "<hr/>",
                "regex": True
            },
            {
                "pattern": r'<div class="footer">Footer text</div>',
                "replacement": r'<section class="footer">Footer text</section>',
                "regex": False
            }
        ]
        result = apply_replacements(content, replacements)
        assert "<hr/>" in result
        assert '<section class="footer">' in result
        assert '<div class="footer">' not in result


class TestReplacementsParser:
    """Test parsing of replacements from .gensi files."""

    def test_parse_replacements(self, temp_dir):
        """Test parsing replacements from .gensi file."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test EPUB"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
content = "div.content"

[[replacements]]
pattern = '<p class="center">* * * *</p>'
replacement = '<hr/>'
regex = false

[[replacements]]
pattern = '<p class="center">[*\\s]+</p>'
replacement = '<hr/>'
regex = true
"""
        gensi_path = temp_dir / 'with_replacements.gensi'
        gensi_path.write_text(content, encoding='utf-8')

        parser = GensiParser(gensi_path)
        assert len(parser.replacements) == 2
        assert parser.replacements[0]['pattern'] == '<p class="center">* * * *</p>'
        assert parser.replacements[0]['replacement'] == '<hr/>'
        assert parser.replacements[0]['regex'] is False
        assert parser.replacements[1]['regex'] is True

    def test_parse_no_replacements(self, temp_dir):
        """Test parsing .gensi file without replacements."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test EPUB"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'no_replacements.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.replacements == []

    def test_replacement_missing_pattern(self, temp_dir):
        """Test that replacement without pattern raises error."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[[replacements]]
replacement = '<hr/>'
regex = false
"""
        gensi_path = temp_dir / 'missing_pattern.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="pattern.*required"):
            GensiParser(gensi_path)

    def test_replacement_missing_replacement(self, temp_dir):
        """Test that replacement without replacement string raises error."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[[replacements]]
pattern = 'foo'
regex = false
"""
        gensi_path = temp_dir / 'missing_replacement.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="replacement.*required"):
            GensiParser(gensi_path)

    def test_replacement_missing_regex(self, temp_dir):
        """Test that replacement without regex flag raises error."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[[replacements]]
pattern = 'foo'
replacement = 'bar'
"""
        gensi_path = temp_dir / 'missing_regex.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="regex.*required"):
            GensiParser(gensi_path)

    def test_replacement_invalid_types(self, temp_dir):
        """Test that replacement with invalid types raises error."""
        from gensi.core.parser import GensiParser

        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[[replacements]]
pattern = 123
replacement = 'bar'
regex = false
"""
        gensi_path = temp_dir / 'invalid_pattern_type.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="pattern.*must be a string"):
            GensiParser(gensi_path)
