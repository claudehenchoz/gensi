"""Tests for HTML sanitizer."""

import pytest
from gensi.core.sanitizer import Sanitizer


class TestSanitizer:
    """Test HTML sanitization for EPUB compliance."""

    @pytest.fixture
    def sanitizer(self):
        """Create a sanitizer instance."""
        return Sanitizer()

    def test_sanitize_basic_html(self, sanitizer):
        """Test sanitizing basic HTML."""
        html = "<p>This is a <strong>test</strong> paragraph.</p>"
        result = sanitizer.sanitize(html)

        assert "<p>" in result
        assert "<strong>" in result
        assert "test" in result

    def test_sanitize_removes_script_tags(self, sanitizer):
        """Test that script tags are removed."""
        html = """
<div>
    <p>Safe content</p>
    <script>alert('XSS');</script>
    <p>More safe content</p>
</div>
"""
        result = sanitizer.sanitize(html)

        assert "Safe content" in result
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_removes_style_tags(self, sanitizer):
        """Test that style tags are removed."""
        html = """
<div>
    <style>body { background: red; }</style>
    <p>Content</p>
</div>
"""
        result = sanitizer.sanitize(html)

        assert "Content" in result
        assert "<style>" not in result
        assert "background: red" not in result

    def test_sanitize_removes_on_event_attributes(self, sanitizer):
        """Test that event handler attributes are removed."""
        html = '<p onclick="alert(1)">Click me</p>'
        result = sanitizer.sanitize(html)

        assert "Click me" in result
        assert "onclick" not in result
        assert "alert" not in result

    def test_sanitize_preserves_safe_attributes(self, sanitizer):
        """Test that safe attributes are preserved."""
        html = '<a href="http://example.com" class="link">Link</a>'
        result = sanitizer.sanitize(html)

        assert "href" in result
        assert "example.com" in result
        assert "Link" in result

    def test_sanitize_preserves_images(self, sanitizer):
        """Test that images are preserved."""
        html = '<img src="/images/test.jpg" alt="Test Image">'
        result = sanitizer.sanitize(html)

        assert "<img" in result
        assert "src" in result
        assert "alt" in result

    def test_sanitize_preserves_lists(self, sanitizer):
        """Test that lists are preserved."""
        html = """
<ul>
    <li>Item 1</li>
    <li>Item 2</li>
</ul>
"""
        result = sanitizer.sanitize(html)

        assert "<ul>" in result or "<ul" in result
        assert "<li>" in result or "<li" in result
        assert "Item 1" in result
        assert "Item 2" in result

    def test_sanitize_preserves_blockquotes(self, sanitizer):
        """Test that blockquotes are preserved."""
        html = "<blockquote>A famous quote</blockquote>"
        result = sanitizer.sanitize(html)

        assert "blockquote" in result
        assert "A famous quote" in result

    def test_sanitize_empty_content(self, sanitizer):
        """Test sanitizing empty content."""
        html = ""
        result = sanitizer.sanitize(html)

        assert result == ""

    def test_sanitize_whitespace_only(self, sanitizer):
        """Test sanitizing whitespace-only content."""
        html = "   \n  \t  "
        result = sanitizer.sanitize(html)

        assert result.strip() == ""

    def test_sanitize_malformed_html(self, sanitizer):
        """Test sanitizing malformed HTML."""
        html = "<p>Unclosed paragraph<div>Nested div"
        result = sanitizer.sanitize(html)

        # Should still extract text content
        assert "Unclosed paragraph" in result
        assert "Nested div" in result

    def test_sanitize_javascript_url(self, sanitizer):
        """Test that javascript: URLs are removed."""
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitizer.sanitize(html)

        assert "Click" in result
        assert "javascript:" not in result.lower()

    def test_sanitize_data_url(self, sanitizer):
        """Test handling of data: URLs."""
        html = '<img src="data:image/png;base64,iVBORw0KGg==" alt="Data image">'
        result = sanitizer.sanitize(html)

        # Data URLs might be allowed or removed depending on sanitizer config
        assert "Data image" in result or "alt" in result

    def test_sanitize_preserves_formatting(self, sanitizer):
        """Test that text formatting is preserved."""
        html = "<p>Text with <em>emphasis</em> and <strong>strong</strong>.</p>"
        result = sanitizer.sanitize(html)

        assert "emphasis" in result
        assert "strong" in result
        assert ("<em>" in result or "<i>" in result)  # em might be converted to i
        assert ("<strong>" in result or "<b>" in result)  # strong might be converted to b
