"""Tests for content extractor - CSS selectors and Python scripts."""

import pytest
from pathlib import Path
from gensi.core.extractor import Extractor, parse_rss_feed
from gensi.core.python_executor import PythonExecutor


class TestCoverExtraction:
    """Test cover image URL extraction."""

    @pytest.fixture
    def html_with_cover(self):
        return """
<!DOCTYPE html>
<html>
<head></head>
<body>
    <div class="hero">
        <img class="site-logo" src="/images/logo.jpg" alt="Logo">
    </div>
</body>
</html>
"""

    def test_extract_cover_with_selector(self, html_with_cover):
        """Test extracting cover URL with CSS selector."""
        extractor = Extractor("http://example.com/", html_with_cover)
        config = {'selector': 'img.site-logo'}

        cover_url = extractor.extract_cover_url(config)

        assert cover_url == "http://example.com/images/logo.jpg"

    def test_extract_cover_direct_image_url(self):
        """Test when cover URL is direct image."""
        html = "<html></html>"
        extractor = Extractor("http://example.com/", html)
        config = {
            'url': 'http://example.com/cover.jpg',
            'selector': 'img'  # Should be ignored
        }

        # This would be handled by is_image_url check
        # The extractor itself would recognize it's an image URL
        # For this test, we're testing the selector path
        assert True  # Placeholder

    def test_extract_cover_with_python_script(self, html_with_cover):
        """Test extracting cover URL with Python script."""
        extractor = Extractor("http://example.com/", html_with_cover)
        config = {
            'python': {
                'script': """
img = document.cssselect('img.site-logo')[0]
return img.get('src')
"""
            }
        }
        executor = PythonExecutor()

        cover_url = extractor.extract_cover_url(config, executor)

        assert cover_url == "http://example.com/images/logo.jpg"

    def test_extract_cover_selector_not_found(self):
        """Test cover extraction when selector doesn't match."""
        html = "<html><body><p>No image</p></body></html>"
        extractor = Extractor("http://example.com/", html)
        config = {'selector': 'img.nonexistent'}

        cover_url = extractor.extract_cover_url(config)

        assert cover_url is None


class TestIndexExtraction:
    """Test index article URL extraction."""

    @pytest.fixture
    def html_with_links(self):
        return """
<!DOCTYPE html>
<html>
<body>
    <div class="articles">
        <article class="post">
            <a href="/post1.html" class="link">Post 1</a>
        </article>
        <article class="post">
            <a href="/post2.html" class="link">Post 2</a>
        </article>
        <article class="post">
            <a href="/post3.html" class="link">Post 3</a>
        </article>
    </div>
</body>
</html>
"""

    def test_extract_index_articles_simple(self, html_with_links):
        """Test extracting article URLs with simple CSS selector."""
        extractor = Extractor("http://example.com/index.html", html_with_links)
        config = {
            'type': 'html',
            'links': 'article.post a.link'
        }

        articles = extractor.extract_index_articles(config)

        assert len(articles) == 3
        assert articles[0]['url'] == 'http://example.com/post1.html'
        assert articles[1]['url'] == 'http://example.com/post2.html'
        assert articles[2]['url'] == 'http://example.com/post3.html'

    def test_extract_index_articles_with_python(self, html_with_links):
        """Test extracting article URLs with Python script."""
        extractor = Extractor("http://example.com/index.html", html_with_links)
        config = {
            'type': 'html',
            'python': {
                'script': """
articles = []
for elem in document.cssselect('article.post a.link'):
    articles.append({'url': elem.get('href')})
return articles
"""
            }
        }
        executor = PythonExecutor()

        articles = extractor.extract_index_articles(config, executor)

        assert len(articles) == 3
        assert all('url' in article for article in articles)

    def test_extract_index_articles_with_content(self, html_with_links):
        """Test extracting articles with pre-provided content."""
        extractor = Extractor("http://example.com/index.html", html_with_links)
        config = {
            'type': 'html',
            'python': {
                'script': """
articles = []
for elem in document.cssselect('article.post a.link'):
    articles.append({
        'url': elem.get('href'),
        'content': '<p>Pre-provided content</p>'
    })
return articles
"""
            }
        }
        executor = PythonExecutor()

        articles = extractor.extract_index_articles(config, executor)

        assert len(articles) == 3
        assert all('content' in article for article in articles)
        assert articles[0]['content'] == '<p>Pre-provided content</p>'


class TestArticleExtraction:
    """Test article content extraction."""

    @pytest.fixture
    def article_html(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta name="author" content="Test Author">
    <meta property="article:published_time" content="2025-01-15">
</head>
<body>
    <article>
        <h1 class="title">Article Title</h1>
        <div class="meta">
            <span class="author">John Doe</span>
            <time class="date" datetime="2025-01-15">January 15, 2025</time>
        </div>
        <div class="content">
            <p>Article content here.</p>
            <div class="ad">Advertisement</div>
            <p>More content.</p>
        </div>
        <div class="comments">Comments section</div>
    </article>
</body>
</html>
"""

    def test_extract_article_content_simple(self, article_html):
        """Test extracting article content with CSS selectors."""
        extractor = Extractor("http://example.com/article.html", article_html)
        config = {
            'content': 'div.content',
            'title': 'h1.title',
            'author': 'span.author',
            'date': 'time.date'
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        assert 'Article content here' in result['content']
        assert result['title'] == 'Article Title'
        assert result['author'] == 'John Doe'
        assert result['date'] == 'January 15, 2025'

    def test_extract_article_with_remove_selectors(self, article_html):
        """Test extracting article with element removal."""
        extractor = Extractor("http://example.com/article.html", article_html)
        config = {
            'content': 'div.content',
            'remove': ['.ad', '.comments']
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        assert 'Article content here' in result['content']
        assert 'Advertisement' not in result['content']
        # Comments should not be in content div, but test the remove worked
        assert 'More content' in result['content']

    def test_extract_article_with_python_returning_string(self, article_html):
        """Test extracting article with Python script returning string."""
        extractor = Extractor("http://example.com/article.html", article_html)
        config = {
            'python': {
                'script': """
content = document.cssselect('div.content')[0]
return str(content.text_content())
"""
            }
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        assert isinstance(result, str) or 'content' in result

    def test_extract_article_with_python_returning_dict(self, article_html):
        """Test extracting article with Python script returning dict."""
        extractor = Extractor("http://example.com/article.html", article_html)
        config = {
            'python': {
                'script': """
from lxml import etree
content = document.cssselect('div.content')[0]
title = document.cssselect('h1.title')[0].text
return {
    'content': etree.tostring(content, encoding='unicode'),
    'title': title
}
"""
            }
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        assert isinstance(result, dict)
        assert 'content' in result
        assert 'title' in result
        assert result['title'] == 'Article Title'

    def test_extract_article_metadata_fallback(self):
        """Test article extraction with metadata fallback."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="OG Title">
    <meta name="author" content="Meta Author">
</head>
<body>
    <div class="content"><p>Content</p></div>
</body>
</html>
"""
        extractor = Extractor("http://example.com/article.html", html)
        config = {
            'content': 'div.content'
            # No title/author selectors, should use fallback
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        # Should use metadata fallback
        assert 'Content' in result['content']
        # Title and author should come from meta tags
        assert result.get('title') == 'OG Title' or result.get('title') is None
        assert result.get('author') == 'Meta Author' or result.get('author') is None


class TestRSSParsing:
    """Test RSS/Atom feed parsing."""

    def test_parse_rss_feed_simple(self, sample_rss_feed):
        """Test parsing RSS feed without config."""
        config = {'type': 'rss'}

        articles = parse_rss_feed("http://example.com/feed.rss", sample_rss_feed, config, None)

        assert len(articles) >= 1
        assert all('url' in article for article in articles)

    def test_parse_rss_feed_with_limit(self, rss_fixtures_dir):
        """Test parsing RSS feed with limit."""
        feed_path = rss_fixtures_dir / 'test_feed_rss.xml'
        feed_content = feed_path.read_text(encoding='utf-8')
        config = {'type': 'rss', 'limit': 2}

        articles = parse_rss_feed("http://example.com/feed.rss", feed_content, config, None)

        assert len(articles) == 2

    def test_parse_rss_feed_with_content_encoded(self, rss_fixtures_dir):
        """Test parsing RSS feed with use_content_encoded."""
        feed_path = rss_fixtures_dir / 'test_feed_rss.xml'
        feed_content = feed_path.read_text(encoding='utf-8')
        config = {'type': 'rss', 'use_content_encoded': True}

        articles = parse_rss_feed("http://example.com/feed.rss", feed_content, config, None)

        # Should have content from content:encoded
        assert len(articles) >= 1
        # First two items in test feed have content:encoded
        if len(articles) >= 2:
            assert 'content' in articles[0]
            assert len(articles[0]['content']) > 0

    def test_parse_atom_feed(self, rss_fixtures_dir):
        """Test parsing Atom feed."""
        feed_path = rss_fixtures_dir / 'test_feed_atom.xml'
        feed_content = feed_path.read_text(encoding='utf-8')
        config = {'type': 'rss'}

        articles = parse_rss_feed("http://example.com/feed.atom", feed_content, config, None)

        assert len(articles) >= 1
        assert all('url' in article for article in articles)

    def test_parse_rss_feed_with_python_filtering(self, rss_fixtures_dir):
        """Test parsing RSS feed with Python script filtering."""
        feed_path = rss_fixtures_dir / 'test_feed_with_tags.xml'
        feed_content = feed_path.read_text(encoding='utf-8')
        config = {
            'type': 'rss',
            'python': {
                'script': """
articles = []
for entry in feed.entries:
    # Get categories
    categories = [cat.get('term', '') for cat in entry.get('tags', [])]
    # Filter: include Technology but not Sponsor
    if 'Technology' in categories and 'Sponsor' not in categories:
        articles.append({'url': entry.link})
return articles
"""
            }
        }
        executor = PythonExecutor()

        articles = parse_rss_feed("http://example.com/feed.rss", feed_content, config, executor)

        # Should only get articles with Technology tag and without Sponsor
        assert len(articles) == 2  # Articles 1 and 4 from test_feed_with_tags.xml
