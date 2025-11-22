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


class TestParserJsonSupport:
    """Test parsing and validation of JSON-related fields."""

    def test_valid_json_index_simple_mode(self, temp_dir):
        """Test valid JSON index with json_path and links in simple mode."""
        content = """
title = "Test JSON EPUB"

[[index]]
url = "http://localhost/graphql"
type = "json"
json_path = "data.magazin.content"
links = ".article-link"

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'json_index.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.indices[0]['type'] == 'json'
        assert parser.indices[0]['json_path'] == 'data.magazin.content'
        assert parser.indices[0]['links'] == '.article-link'

    def test_valid_json_index_python_mode(self, temp_dir):
        """Test valid JSON index with Python override (no json_path needed)."""
        content = """
title = "Test JSON EPUB"

[[index]]
url = "http://localhost/graphql"
type = "json"

[index.python]
script = '''
articles = []
for item in data['items']:
    articles.append({'url': item['url']})
return articles
'''

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'json_index_python.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.indices[0]['type'] == 'json'
        assert 'python' in parser.indices[0]

    def test_json_index_missing_json_path(self, temp_dir):
        """Test that JSON index without json_path in simple mode raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/graphql"
type = "json"
links = ".article-link"
"""
        gensi_path = temp_dir / 'json_missing_path.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="json_path.*required.*JSON type"):
            GensiParser(gensi_path)

    def test_json_index_missing_links(self, temp_dir):
        """Test that JSON index without links in simple mode raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/graphql"
type = "json"
json_path = "data.content"
"""
        gensi_path = temp_dir / 'json_missing_links.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="links.*required.*JSON type"):
            GensiParser(gensi_path)

    def test_valid_article_json_string_path(self, temp_dir):
        """Test valid article with JSON response_type and string json_path."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
response_type = "json"
json_path = "data.reportage.content"
content = "div.content"
"""
        gensi_path = temp_dir / 'article_json_string.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.article['response_type'] == 'json'
        assert parser.article['json_path'] == 'data.reportage.content'

    def test_valid_article_json_dict_path(self, temp_dir):
        """Test valid article with JSON response_type and dict json_path."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
response_type = "json"

[article.json_path]
content = "data.reportage.content"
title = "data.reportage.title"
author = "data.reportage.author"
"""
        gensi_path = temp_dir / 'article_json_dict.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.article['response_type'] == 'json'
        assert isinstance(parser.article['json_path'], dict)
        assert parser.article['json_path']['content'] == 'data.reportage.content'
        assert parser.article['json_path']['title'] == 'data.reportage.title'

    def test_article_json_dict_missing_content(self, temp_dir):
        """Test that article json_path dict without 'content' key raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
response_type = "json"

[article.json_path]
title = "data.title"
"""
        gensi_path = temp_dir / 'article_json_no_content.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="json_path dict must have 'content' key"):
            GensiParser(gensi_path)

    def test_article_invalid_response_type(self, temp_dir):
        """Test that invalid response_type raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
response_type = "xml"
content = "div.content"
"""
        gensi_path = temp_dir / 'article_invalid_type.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="response_type.*must be.*html.*json"):
            GensiParser(gensi_path)

    def test_article_json_missing_json_path(self, temp_dir):
        """Test that article with response_type='json' without json_path raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[article]
response_type = "json"
content = "div.content"
"""
        gensi_path = temp_dir / 'article_json_no_path.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="json_path.*required.*response_type='json'"):
            GensiParser(gensi_path)

    def test_valid_url_transform_simple_mode(self, temp_dir):
        """Test valid url_transform in simple mode with pattern and template."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/graphql"
type = "json"
json_path = "data.content"
links = ".article-link"

[index.url_transform]
pattern = '/reportage/([^/]+)/'
template = 'https://api.com/graphql?slug={1}'

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'url_transform_simple.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert 'url_transform' in parser.indices[0]
        assert parser.indices[0]['url_transform']['pattern'] == '/reportage/([^/]+)/'
        assert parser.indices[0]['url_transform']['template'] == 'https://api.com/graphql?slug={1}'

    def test_valid_url_transform_python_mode(self, temp_dir):
        """Test valid url_transform in Python mode."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[index.url_transform.python]
script = '''
import re
match = re.search(r'/article/([^/]+)/', url)
if match:
    return f"https://api.com/article/{match.group(1)}"
return url
'''

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'url_transform_python.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert 'url_transform' in parser.indices[0]
        assert 'python' in parser.indices[0]['url_transform']

    def test_url_transform_missing_pattern(self, temp_dir):
        """Test that url_transform without pattern in simple mode raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[index.url_transform]
template = 'https://api.com/{1}'

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'url_transform_no_pattern.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="url_transform requires 'pattern'"):
            GensiParser(gensi_path)

    def test_url_transform_missing_template(self, temp_dir):
        """Test that url_transform without template in simple mode raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[index.url_transform]
pattern = '/article/([^/]+)/'

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'url_transform_no_template.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="url_transform requires 'template'"):
            GensiParser(gensi_path)

    def test_url_transform_mixed_modes_error(self, temp_dir):
        """Test that url_transform with both Python and pattern/template raises error."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
links = "a"

[index.url_transform]
pattern = '/article/([^/]+)/'
template = 'https://api.com/{1}'

[index.url_transform.python]
script = "return url"

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'url_transform_mixed.gensi'
        gensi_path.write_text(content)

        with pytest.raises(ValueError, match="cannot have both 'python' and 'pattern'"):
            GensiParser(gensi_path)

    def test_html_index_with_response_type_json(self, temp_dir):
        """Test HTML index with response_type='json' (fetch HTML, but it's actually JSON)."""
        content = """
title = "Test"

[[index]]
url = "http://localhost/index.html"
type = "html"
response_type = "json"
json_path = "data.html"
links = "a"

[article]
content = "div.content"
"""
        gensi_path = temp_dir / 'html_response_json.gensi'
        gensi_path.write_text(content)

        parser = GensiParser(gensi_path)
        assert parser.indices[0]['type'] == 'html'
        assert parser.indices[0]['response_type'] == 'json'
        assert parser.indices[0]['json_path'] == 'data.html'
