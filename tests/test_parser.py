"""Tests for GensiParser - TOML parsing and validation."""

import pytest
from pathlib import Path
from gensi.core.parser import GensiParser


class TestParserValidFiles:
    """Test parsing of valid .gensi files."""

    def test_parse_simple_gensi(self, valid_gensi_simple):
        """Test parsing a simple valid .gensi file."""
        parser = GensiParser(valid_gensi_simple)

        assert parser.title == "Test EPUB"
        assert parser.author == "Test Author"
        assert parser.language == "en"
        assert len(parser.indices) == 1
        assert parser.indices[0]['url'] == "http://localhost/blog_index.html"
        assert parser.indices[0]['type'] == "html"

    def test_parse_with_cover(self, valid_gensi_with_cover):
        """Test parsing .gensi file with cover section."""
        parser = GensiParser(valid_gensi_with_cover)

        assert parser.cover is not None
        assert parser.cover['url'] == "http://localhost/cover_page.html"
        assert parser.cover['selector'] == "img.site-logo"

    def test_parse_multi_index(self, valid_gensi_multi_index):
        """Test parsing .gensi file with multiple indices."""
        parser = GensiParser(valid_gensi_multi_index)

        assert len(parser.indices) == 2
        assert parser.indices[0]['name'] == "Blog Posts"
        assert parser.indices[0]['type'] == "html"
        assert parser.indices[1]['name'] == "RSS Feed"
        assert parser.indices[1]['type'] == "rss"

    def test_parse_with_python_script(self, valid_gensi_with_python):
        """Test parsing .gensi file with Python scripts."""
        parser = GensiParser(valid_gensi_with_python)

        assert len(parser.indices) == 1
        assert 'python' in parser.indices[0]
        assert 'script' in parser.indices[0]['python']

    def test_parse_article_config(self, valid_gensi_simple):
        """Test parsing article configuration."""
        parser = GensiParser(valid_gensi_simple)

        assert parser.article is not None
        assert parser.article['content'] == "div.article-content"
        assert parser.article['title'] == "h1.article-title"
        assert parser.article['author'] == "span.author"
        assert parser.article['date'] == "time.published"
        assert '.sidebar' in parser.article['remove']

    def test_optional_fields_none(self, temp_dir):
        """Test that optional fields default to None."""
        content = """
title = "Minimal EPUB"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'minimal.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)

        assert parser.title == "Minimal EPUB"
        assert parser.author is None
        assert parser.language is None
        assert parser.cover is None

    def test_get_article_config_global(self, valid_gensi_simple):
        """Test getting global article config."""
        parser = GensiParser(valid_gensi_simple)

        index_data = parser.indices[0]
        article_config = parser.get_article_config(index_data)

        assert article_config == parser.article

    def test_get_article_config_no_override(self, temp_dir):
        """Test that article config is returned when no override exists."""
        content = """
title = "Override Test"

[article]
content = "div.global-content"
title = "h1.global-title"

[[index]]
url = "http://localhost/index1.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'no_override.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)

        # Index uses global config
        config = parser.get_article_config(parser.indices[0])
        assert config['content'] == "div.global-content"
        assert config['title'] == "h1.global-title"


class TestParserValidation:
    """Test validation of .gensi files."""

    def test_missing_title(self, invalid_gensi_no_title):
        """Test that missing title raises ValueError."""
        with pytest.raises(ValueError, match="title.*required"):
            GensiParser(invalid_gensi_no_title)

    def test_empty_title(self, temp_dir):
        """Test that empty title raises ValueError."""
        content = """
title = "   "

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'empty_title.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="title.*non-empty"):
            GensiParser(gensi_path)

    def test_missing_index(self, invalid_gensi_no_index):
        """Test that missing index section raises ValueError."""
        with pytest.raises(ValueError, match="index.*required"):
            GensiParser(invalid_gensi_no_index)

    def test_invalid_index_type(self, invalid_gensi_wrong_type):
        """Test that invalid index type raises ValueError."""
        with pytest.raises(ValueError, match="type.*must be.*html.*rss"):
            GensiParser(invalid_gensi_wrong_type)

    def test_html_index_missing_links(self, temp_dir):
        """Test that HTML index without links or python raises ValueError."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
"""
        gensi_path = temp_dir / 'no_links.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="links.*required"):
            GensiParser(gensi_path)

    def test_index_missing_url(self, temp_dir):
        """Test that index without URL raises ValueError."""
        content = """
title = "Test"

[[index]]
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'no_url.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="url.*required"):
            GensiParser(gensi_path)

    def test_index_missing_type(self, temp_dir):
        """Test that index without type raises ValueError."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
links = "a"
"""
        gensi_path = temp_dir / 'no_type.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="type.*required"):
            GensiParser(gensi_path)

    def test_multiple_index_missing_name(self, invalid_gensi_multi_no_name):
        """Test that multiple indices without names raise ValueError."""
        with pytest.raises(ValueError, match="name.*required.*multiple"):
            GensiParser(invalid_gensi_multi_no_name)

    def test_multiple_index_empty_name(self, temp_dir):
        """Test that multiple indices with empty names raise ValueError."""
        content = """
title = "Test"

[[index]]
name = "First Section"
url = "http://localhost/index1.html"
type = "html"
links = "a"

[[index]]
name = "  "
url = "http://localhost/index2.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'empty_name.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="name.*required"):
            GensiParser(gensi_path)

    def test_cover_missing_url(self, temp_dir):
        """Test that cover section without URL raises ValueError."""
        content = """
title = "Test"

[cover]
selector = "img"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'cover_no_url.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="[Cc]over.*url.*required"):
            GensiParser(gensi_path)

    def test_article_missing_content_selector(self, temp_dir):
        """Test that article section without content selector raises ValueError."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
title = "h1"
"""
        gensi_path = temp_dir / 'article_no_content.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="[Aa]rticle.*content.*required"):
            GensiParser(gensi_path)

    def test_html_index_with_python_no_links(self, temp_dir):
        """Test that HTML index with Python script doesn't require links."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"

[index.python]
script = "return []"
"""
        gensi_path = temp_dir / 'html_python.gensi'
        gensi_path.write_text(content)

        # Should not raise
        parser = GensiParser(gensi_path)
        assert len(parser.indices) == 1

    def test_article_with_python_no_content(self, temp_dir):
        """Test that article with Python script doesn't require content selector."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article.python]
script = "return '<p>test</p>'"
"""
        gensi_path = temp_dir / 'article_python.gensi'
        gensi_path.write_text(content)

        # Should not raise
        parser = GensiParser(gensi_path)
        assert parser.article is not None

    def test_single_index_without_name(self, temp_dir):
        """Test that single index doesn't require name field."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"
"""
        gensi_path = temp_dir / 'single_no_name.gensi'
        gensi_path.write_text(content)

        # Should not raise
        parser = GensiParser(gensi_path)
        assert len(parser.indices) == 1
        assert 'name' not in parser.indices[0] or parser.indices[0].get('name') is None


class TestParserEdgeCases:
    """Test edge cases and special scenarios."""

    def test_rss_index_with_limit(self, temp_dir):
        """Test RSS index with limit field."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/feed.rss"
type = "rss"
limit = 10
"""
        gensi_path = temp_dir / 'rss_limit.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.indices[0]['limit'] == 10

    def test_rss_index_with_use_content_encoded(self, temp_dir):
        """Test RSS index with use_content_encoded field."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/feed.rss"
type = "rss"
use_content_encoded = true
"""
        gensi_path = temp_dir / 'rss_content.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.indices[0]['use_content_encoded'] is True

    def test_article_with_remove_array(self, valid_gensi_simple):
        """Test article with remove selectors array."""
        parser = GensiParser(valid_gensi_simple)

        assert 'remove' in parser.article
        assert isinstance(parser.article['remove'], list)
        assert len(parser.article['remove']) == 1

    def test_article_images_config(self, temp_dir):
        """Test article with images configuration."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
content = "div.content"
images = false
"""
        gensi_path = temp_dir / 'article_images.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.article['images'] is False

    def test_malformed_toml(self, temp_dir):
        """Test that malformed TOML raises exception."""
        content = """
title = "Test
this is not valid TOML
"""
        gensi_path = temp_dir / 'malformed.gensi'
        gensi_path.write_text(content)

        with pytest.raises(Exception):  # tomllib will raise an exception
            GensiParser(gensi_path)

    def test_nonexistent_file(self):
        """Test that nonexistent file raises exception."""
        with pytest.raises(FileNotFoundError):
            GensiParser('nonexistent.gensi')
