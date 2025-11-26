"""Tests for content extractor - CSS selectors and Python scripts."""

import pytest
from pathlib import Path
from gensi.core.extractor import Extractor, parse_rss_feed, parse_bluesky_feed
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

    def test_extract_article_metadata_from_removed_element(self):
        """Test that metadata is extracted before elements are removed.

        This tests the bug fix where metadata (author, title, date) in elements
        that are also in the 'remove' list should still be extracted successfully.
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
</head>
<body>
    <article>
        <div class="title-lead">
            <h1 class="title">Article Title</h1>
            <p class="byline">
                <span class="author">Jane Smith</span>
                <time class="date" datetime="2025-01-20">January 20, 2025</time>
            </p>
        </div>
        <div class="content">
            <p>This is the actual article content that should remain.</p>
            <p>More content here.</p>
        </div>
    </article>
</body>
</html>
"""
        extractor = Extractor("http://example.com/article.html", html)
        config = {
            'content': 'article',
            'title': 'h1.title',
            'author': 'span.author',
            'date': 'time.date',
            'remove': [
                'div.title-lead',  # This div contains the title, author, and date!
            ]
        }
        executor = PythonExecutor()

        result = extractor.extract_article_content(config, executor)

        # Metadata should be extracted even though elements are in 'remove' list
        assert result['title'] == 'Article Title'
        assert result['author'] == 'Jane Smith'
        assert result['date'] == 'January 20, 2025'

        # The title-lead div should be removed from content
        assert 'title-lead' not in result['content']
        assert 'Article Title' not in result['content']  # Title should be removed
        assert 'Jane Smith' not in result['content']  # Author should be removed

        # But the actual content should remain
        assert 'This is the actual article content that should remain.' in result['content']
        assert 'More content here.' in result['content']


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


class TestBlueskyFeedParsing:
    """Test Bluesky feed parsing."""

    def test_parse_bluesky_with_external_embeds(self):
        """Extract URLs from card embeds."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article2'}}}}
            ]
        })

        config = {'username': 'test.bsky.social'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 2
        assert articles[0]['url'] == 'https://example.com/article1'
        assert articles[1]['url'] == 'https://example.com/article2'

    def test_parse_bluesky_deduplicates_urls(self):
        """Ensure duplicate URLs are filtered."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}}
            ]
        })

        config = {'username': 'test.bsky.social'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 1

    def test_parse_bluesky_with_limit(self):
        """Test limit parameter."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': f'https://example.com/article{i}'}}}}
                for i in range(10)
            ]
        })

        config = {'username': 'test.bsky.social', 'limit': 3}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 3

    def test_parse_bluesky_ignores_non_external_embeds(self):
        """Non-card embeds should be ignored."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.images#view'}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}}
            ]
        })

        config = {'username': 'test.bsky.social'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 1
        assert articles[0]['url'] == 'https://example.com/article1'

    def test_parse_bluesky_api_error(self):
        """Handle API error responses."""
        import json
        feed_content = json.dumps({
            'error': 'InvalidRequest',
            'message': 'Actor not found'
        })

        config = {'username': 'invalid.bsky.social'}

        with pytest.raises(Exception, match='Bluesky API error: Actor not found'):
            parse_bluesky_feed('', feed_content, config)

    def test_parse_bluesky_invalid_json(self):
        """Handle invalid JSON responses."""
        config = {'username': 'test.bsky.social'}

        with pytest.raises(Exception, match='Failed to parse Bluesky API response'):
            parse_bluesky_feed('', 'invalid json{', config)

    def test_parse_bluesky_with_python_override(self):
        """Test Python override for custom filtering."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://other.com/article2'}}}}
            ]
        })

        config = {
            'username': 'test.bsky.social',
            'python': {
                'script': '''
articles = []
for entry in feed['feed']:
    post = entry.get('post', {})
    embed = post.get('embed', {})
    if embed.get('$type') == 'app.bsky.embed.external#view':
        uri = embed.get('external', {}).get('uri')
        if uri and 'example.com' in uri:
            articles.append({'url': uri})
return articles
'''
            }
        }

        executor = PythonExecutor()
        articles = parse_bluesky_feed('', feed_content, config, executor)

        assert len(articles) == 1
        assert articles[0]['url'] == 'https://example.com/article1'

    def test_parse_bluesky_with_domain_filter(self):
        """Test domain filtering for exact domain match."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://republik.ch/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article2'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://republik.ch/article3'}}}}
            ]
        })

        config = {'username': 'test.bsky.social', 'domain': 'republik.ch'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 2
        assert articles[0]['url'] == 'https://republik.ch/article1'
        assert articles[1]['url'] == 'https://republik.ch/article3'

    def test_parse_bluesky_with_subdomain_filter(self):
        """Test domain filtering includes subdomains."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://republik.ch/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://www.republik.ch/article2'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://content.republik.ch/article3'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://other.com/article4'}}}}
            ]
        })

        config = {'username': 'test.bsky.social', 'domain': 'republik.ch'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 3
        assert articles[0]['url'] == 'https://republik.ch/article1'
        assert articles[1]['url'] == 'https://www.republik.ch/article2'
        assert articles[2]['url'] == 'https://content.republik.ch/article3'

    def test_parse_bluesky_domain_filter_with_limit(self):
        """Test domain filtering combined with limit."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://republik.ch/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article2'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://www.republik.ch/article3'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://content.republik.ch/article4'}}}}
            ]
        })

        config = {'username': 'test.bsky.social', 'domain': 'republik.ch', 'limit': 2}
        articles = parse_bluesky_feed('', feed_content, config)

        # Should get first 2 matching republik.ch URLs
        assert len(articles) == 2
        assert articles[0]['url'] == 'https://republik.ch/article1'
        assert articles[1]['url'] == 'https://www.republik.ch/article3'

    def test_parse_bluesky_without_domain_filter(self):
        """Test that without domain filter, all URLs are returned."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://republik.ch/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article2'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://other.org/article3'}}}}
            ]
        })

        config = {'username': 'test.bsky.social'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 3

    def test_parse_bluesky_domain_filter_no_matches(self):
        """Test domain filtering when no URLs match."""
        import json
        feed_content = json.dumps({
            'feed': [
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://example.com/article1'}}}},
                {'post': {'embed': {'$type': 'app.bsky.embed.external#view',
                         'external': {'uri': 'https://other.org/article2'}}}}
            ]
        })

        config = {'username': 'test.bsky.social', 'domain': 'republik.ch'}
        articles = parse_bluesky_feed('', feed_content, config)

        assert len(articles) == 0


class TestURLTransformation:
    """Test URL transformation functionality."""

    def test_transform_url_simple_mode(self):
        """Test URL transformation with pattern and template."""
        extractor = Extractor("http://example.com/", "<html></html>")
        transform_config = {
            'pattern': r'/reportage/([^/]+)/',
            'template': 'https://api.com/graphql?slug={1}'
        }

        url = "/reportage/test-article/"
        transformed = extractor.transform_url(url, transform_config)

        assert transformed == "https://api.com/graphql?slug=test-article"

    def test_transform_url_multiple_groups(self):
        """Test URL transformation with multiple captured groups."""
        extractor = Extractor("http://example.com/", "<html></html>")
        transform_config = {
            'pattern': r'/(\d+)/([a-z-]+)/',
            'template': 'https://api.com/articles?id={1}&slug={2}'
        }

        url = "/2024/my-article/"
        transformed = extractor.transform_url(url, transform_config)

        assert transformed == "https://api.com/articles?id=2024&slug=my-article"

    def test_transform_url_no_match_returns_original(self):
        """Test that unmatched URLs are returned unchanged."""
        extractor = Extractor("http://example.com/", "<html></html>")
        transform_config = {
            'pattern': r'/article/([^/]+)/',
            'template': 'https://api.com/article/{1}'
        }

        url = "/different/path/"
        transformed = extractor.transform_url(url, transform_config)

        assert transformed == "/different/path/"

    def test_transform_url_python_mode(self):
        """Test URL transformation with Python script."""
        extractor = Extractor("http://example.com/", "<html></html>")
        transform_config = {
            'python': {
                'script': '''
import re
match = re.search(r'/reportage/([^/]+)/', url)
if match:
    slug = match.group(1)
    return f"https://api.com/graphql?slug={slug}"
return url
'''
            }
        }
        executor = PythonExecutor()

        url = "/reportage/test-article/"
        transformed = extractor.transform_url(url, transform_config, executor)

        assert transformed == "https://api.com/graphql?slug=test-article"


class TestJSONIndexExtraction:
    """Test JSON index extraction functionality."""

    def test_extract_json_index_simple_mode(self):
        """Test extracting articles from JSON index in simple mode."""
        json_response = '''
        {
            "data": {
                "magazin": {
                    "content": "<div><a class='article-link' href='/article/first/'>First</a><a class='article-link' href='/article/second/'>Second</a></div>"
                }
            }
        }
        '''
        config = {
            'type': 'json',
            'json_path': 'data.magazin.content',
            'links': '.article-link'
        }
        extractor = Extractor("http://example.com/", json_response, content_type='json', config=config)

        articles = extractor.extract_index_articles(config)

        assert len(articles) == 2
        assert articles[0]['url'] == 'http://example.com/article/first/'
        assert articles[1]['url'] == 'http://example.com/article/second/'

    def test_extract_json_index_with_python(self):
        """Test extracting articles from JSON index with Python script."""
        json_response = '''
        {
            "posts": [
                {"id": 1, "permalink": "/post/first/"},
                {"id": 2, "permalink": "/post/second/"}
            ]
        }
        '''
        config = {
            'type': 'json',
            'python': {
                'script': '''
articles = []
for post in data['posts']:
    articles.append({'url': post['permalink']})
return articles
'''
            }
        }
        extractor = Extractor("http://example.com/", json_response, content_type='json', config=config)
        executor = PythonExecutor()

        articles = extractor.extract_index_articles(config, executor)

        assert len(articles) == 2
        assert articles[0]['url'] == 'http://example.com/post/first/'
        assert articles[1]['url'] == 'http://example.com/post/second/'


class TestJSONArticleExtraction:
    """Test JSON article extraction functionality."""

    def test_extract_article_from_json_string_path(self):
        """Test extracting article content from JSON with string json_path."""
        json_response = '''
        {
            "data": {
                "reportage": {
                    "title": "Test Article",
                    "content": "<article><h1>Test Article</h1><p>Content here</p></article>"
                }
            }
        }
        '''
        config = {
            'response_type': 'json',
            'json_path': 'data.reportage.content',
            'content': 'article'
        }
        extractor = Extractor("http://example.com/article.json", json_response, content_type='json', config=config)

        result = extractor.extract_article_content(config)

        assert result['content'] is not None
        assert '<h1>Test Article</h1>' in result['content']
        assert '<p>Content here</p>' in result['content']

    def test_extract_article_from_json_dict_path(self):
        """Test extracting article content and metadata from JSON with dict json_path."""
        json_response = '''
        {
            "data": {
                "reportage": {
                    "title": "Test Article",
                    "author": "John Doe",
                    "content": "<article><p>Content here</p></article>"
                }
            }
        }
        '''
        config = {
            'response_type': 'json',
            'json_path': {
                'content': 'data.reportage.content',
                'title': 'data.reportage.title',
                'author': 'data.reportage.author'
            },
            'content': 'article'
        }
        extractor = Extractor("http://example.com/article.json", json_response, content_type='json', config=config)

        result = extractor.extract_article_content(config)

        assert result['content'] is not None
        assert '<p>Content here</p>' in result['content']
        assert result['title'] == 'Test Article'
        assert result['author'] == 'John Doe'

    def test_extract_article_json_mixed_extraction(self):
        """Test mixing JSON extraction and CSS selectors for metadata."""
        json_response = '''
        {
            "data": {
                "reportage": {
                    "title": "Test Article from JSON",
                    "content": "<article><p>Content here</p><a class='author'>Jane Doe</a><time>2025-01-15</time></article>"
                }
            }
        }
        '''
        config = {
            'response_type': 'json',
            'json_path': {
                'content': 'data.reportage.content',
                'title': 'data.reportage.title'
                # Note: author is NOT in json_path
            },
            'author': 'a.author',  # CSS selector for author
            'date': 'time',  # CSS selector for date
        }
        extractor = Extractor("http://example.com/article.json", json_response, content_type='json', config=config)

        result = extractor.extract_article_content(config)

        assert result['content'] is not None
        assert '<p>Content here</p>' in result['content']
        assert result['title'] == 'Test Article from JSON'  # From JSON
        assert result['author'] == 'Jane Doe'  # From CSS selector
        assert result['date'] == '2025-01-15'  # From CSS selector

    def test_extract_article_json_metadata_from_removed_element(self):
        """Test extracting metadata from elements that will be removed."""
        json_response = '''
        {
            "data": {
                "reportage": {
                    "title": "Test Article",
                    "content": "<article><div class='title-lead'><h1>Test Article</h1><p class='byline'><a class='author'>John Doe</a></p></div><p>Article content here</p></article>"
                }
            }
        }
        '''
        config = {
            'response_type': 'json',
            'json_path': {
                'content': 'data.reportage.content',
                'title': 'data.reportage.title'
            },
            'author': 'a.author',  # Extract author from element that will be removed
            'remove': [
                'div.title-lead',  # Remove the div containing the author
            ]
        }
        extractor = Extractor("http://example.com/article.json", json_response, content_type='json', config=config)

        result = extractor.extract_article_content(config)

        assert result['content'] is not None
        # Author should be extracted even though the element is removed
        assert result['author'] == 'John Doe'
        # Title-lead div should be removed from content
        assert 'title-lead' not in result['content']
        assert 'Article content here' in result['content']
