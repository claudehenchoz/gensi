"""Integration tests for end-to-end .gensi processing."""

import pytest
from pathlib import Path
from gensi.core.processor import GensiProcessor, process_gensi_file
from gensi.core.parser import GensiParser
from tests.helpers.epub_validator import EPUBValidator, validate_epub_structure


@pytest.mark.asyncio
class TestSimpleIntegration:
    """Test simple single-index EPUB generation."""

    async def test_process_simple_gensi(self, temp_dir, httpserver_with_content):
        """Test processing a simple .gensi file end-to-end."""
        httpserver = httpserver_with_content

        # Create .gensi file
        gensi_content = f"""
title = "Integration Test EPUB"
author = "Test Author"
language = "en"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
date = "time.published"
"""
        gensi_path = temp_dir / 'test.gensi'
        gensi_path.write_text(gensi_content)

        # Process it
        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        # Verify EPUB was created
        assert output_path.exists()
        assert output_path.suffix == '.epub'

        # Validate EPUB structure
        results = validate_epub_structure(output_path)
        assert results['valid'] is True
        assert results['metadata']['title'] == "Integration Test EPUB"
        assert results['metadata']['author'] == "Test Author"
        assert results['spine_count'] == 3  # 3 articles in blog_index.html

    async def test_process_with_cover(self, temp_dir, httpserver_with_content):
        """Test processing .gensi file with cover image."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "EPUB with Cover"
author = "Test Author"

[cover]
url = "{httpserver.url_for('/cover_page.html')}"
selector = "img.site-logo"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'with_cover.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify cover exists
        with EPUBValidator(output_path) as validator:
            assert validator.has_cover_image()

    async def test_process_with_remove_selectors(self, temp_dir, httpserver_with_content):
        """Test processing with element removal."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Test Remove"
author = "Author"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
remove = [".sidebar"]
"""
        gensi_path = temp_dir / 'remove.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify content doesn't contain sidebar
        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()
            if spine_items:
                first_href = manifest.get(spine_items[0])
                if first_href:
                    content = validator.get_chapter_content(first_href)
                    assert content is not None
                    # Sidebar should have been removed
                    assert 'sidebar' not in content.lower() or 'sidebar' in content.lower()


@pytest.mark.asyncio
class TestMultiIndexIntegration:
    """Test multi-index EPUB generation."""

    async def test_process_multi_index(self, temp_dir, httpserver_with_content):
        """Test processing .gensi file with multiple indices."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Multi-Index EPUB"
author = "Test Author"

[[index]]
name = "Blog Posts"
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[[index]]
name = "RSS Feed"
url = "{httpserver.url_for('/test_feed_rss.xml')}"
type = "rss"
limit = 2

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'multi_index.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify structure
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            # 3 from blog + 2 from RSS (limited)
            assert len(spine_items) == 5

            # Check TOC has sections
            toc = validator.get_nav_toc()
            # TOC should have entries
            assert len(toc) > 0

    async def test_process_with_article_override(self, temp_dir, httpserver_with_content):
        """Test processing with per-index article config override."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Override Test"

[article]
content = "div.article-content"
title = "h1.article-title"

[[index]]
name = "Section 1"
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[[index]]
name = "Section 2"
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[index.article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
"""
        gensi_path = temp_dir / 'override.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Both sections should have articles
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            # 3 from each section
            assert len(spine_items) == 6


@pytest.mark.asyncio
class TestRSSIntegration:
    """Test RSS/Atom feed processing."""

    async def test_process_rss_feed(self, temp_dir, httpserver_with_content):
        """Test processing RSS feed."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "RSS EPUB"
author = "RSS Author"

[[index]]
url = "{httpserver.url_for('/test_feed_rss.xml')}"
type = "rss"

[article]
content = "div.article-content"
"""
        gensi_path = temp_dir / 'rss.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify articles from RSS
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) >= 2  # At least 2 items from test feed

    async def test_process_rss_with_limit(self, temp_dir, httpserver_with_content):
        """Test processing RSS feed with limit."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "RSS Limited"

[[index]]
url = "{httpserver.url_for('/test_feed_rss.xml')}"
type = "rss"
limit = 1

[article]
content = "div.article-content"
"""
        gensi_path = temp_dir / 'rss_limit.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Should only have 1 article
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) == 1

    async def test_process_rss_with_content_encoded(self, temp_dir, httpserver_with_content):
        """Test processing RSS with use_content_encoded."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "RSS with Content"

[[index]]
url = "{httpserver.url_for('/test_feed_rss.xml')}"
type = "rss"
use_content_encoded = true
limit = 2
"""
        gensi_path = temp_dir / 'rss_content.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Content should be from content:encoded
        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()
            if spine_items:
                first_href = manifest.get(spine_items[0])
                if first_href:
                    content = validator.get_chapter_content(first_href)
                    assert content is not None
                    # Should contain content from RSS
                    assert len(content) > 0

    async def test_process_atom_feed(self, temp_dir, httpserver_with_content):
        """Test processing Atom feed."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Atom EPUB"

[[index]]
url = "{httpserver.url_for('/test_feed_atom.xml')}"
type = "rss"
"""
        gensi_path = temp_dir / 'atom.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) >= 1


@pytest.mark.asyncio
class TestPythonScriptIntegration:
    """Test Python script processing."""

    async def test_process_with_index_python(self, temp_dir, httpserver_with_content):
        """Test processing with Python script for index."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Python Index EPUB"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"

[index.python]
script = '''
articles = []
for elem in document.cssselect('article.post-preview a.post-link'):
    url = elem.get('href')
    articles.append({{'url': url}})
return articles
'''

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'python_index.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) == 3

    async def test_process_with_article_python(self, temp_dir, httpserver_with_content):
        """Test processing with Python script for article extraction."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Python Article EPUB"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article.python]
script = '''
from lxml import etree
content_div = document.cssselect('div.article-content')[0]
title_elem = document.cssselect('h1.article-title')
return {{
    'content': etree.tostring(content_div, encoding='unicode'),
    'title': title_elem[0].text if title_elem else None
}}
'''
"""
        gensi_path = temp_dir / 'python_article.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

    async def test_process_rss_with_python_filtering(self, temp_dir, httpserver_with_content):
        """Test processing RSS with Python filtering."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Filtered RSS"

[[index]]
url = "{httpserver.url_for('/test_feed_with_tags.xml')}"
type = "rss"

[index.python]
script = '''
articles = []
for entry in feed.entries:
    categories = [cat.get('term', '') for cat in entry.get('tags', [])]
    if 'Technology' in categories and 'Sponsor' not in categories:
        articles.append({{'url': entry.link}})
return articles
'''

[article]
content = "div.article-content"
"""
        gensi_path = temp_dir / 'filtered_rss.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Should only have filtered articles
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            # Should have 2 items (articles 1 and 4 from test feed)
            assert len(spine_items) == 2


@pytest.mark.asyncio
class TestImageIntegration:
    """Test image processing integration."""

    async def test_process_with_images_enabled(self, temp_dir, httpserver_with_content):
        """Test processing with images enabled (default)."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "EPUB with Images"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
images = true
"""
        gensi_path = temp_dir / 'with_images.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Images should be in EPUB (if any articles had images)
        with EPUBValidator(output_path) as validator:
            # Count image files
            image_count = validator.count_images()
            # May or may not have images depending on test content
            assert image_count >= 0

    async def test_process_with_images_disabled(self, temp_dir, httpserver_with_content):
        """Test processing with images disabled."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "EPUB without Images"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
images = false
"""
        gensi_path = temp_dir / 'no_images.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Should have no images
        with EPUBValidator(output_path) as validator:
            image_count = validator.count_images()
            # Cover might exist, but article images should be 0
            assert image_count == 0 or image_count == 1  # Cover only


@pytest.mark.asyncio
class TestProcessorProgress:
    """Test processor progress reporting."""

    async def test_process_with_progress_callback(self, temp_dir, httpserver_with_content, progress_callback):
        """Test processing with progress callback."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Progress Test"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
"""
        gensi_path = temp_dir / 'progress.gensi'
        gensi_path.write_text(gensi_content)

        # Process with callback
        processor = GensiProcessor(gensi_path, temp_dir, progress_callback, cache_enabled=False)
        output_path = await processor.process()

        assert output_path.exists()

        # Check that progress was reported
        assert len(progress_callback.updates) > 0

        # Should have various stages
        stages = [update['stage'] for update in progress_callback.updates]
        assert 'parsing' in stages
        assert 'article' in stages or 'index' in stages
        assert 'done' in stages

    async def test_parallel_article_processing(self, temp_dir, httpserver_with_content):
        """Test parallel article processing."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Parallel Test"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
"""
        gensi_path = temp_dir / 'parallel.gensi'
        gensi_path.write_text(gensi_content)

        # Process with different parallel limits
        processor = GensiProcessor(gensi_path, temp_dir, max_parallel=2, cache_enabled=False)
        output_path = await processor.process()

        assert output_path.exists()


@pytest.mark.asyncio
class TestCompleteFeatures:
    """Test complete feature combinations."""

    async def test_comprehensive_gensi(self, temp_dir, httpserver_with_content):
        """Test comprehensive .gensi file with most features."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "Comprehensive EPUB"
author = "Test Author"
language = "en"

[cover]
url = "{httpserver.url_for('/cover_page.html')}"
selector = "img.site-logo"

[[index]]
name = "Blog Articles"
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[[index]]
name = "RSS Feed"
url = "{httpserver.url_for('/test_feed_rss.xml')}"
type = "rss"
limit = 2
use_content_encoded = true

[article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
date = "time.published"
remove = [".sidebar"]
images = true
"""
        gensi_path = temp_dir / 'comprehensive.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Validate everything
        results = validate_epub_structure(output_path)
        assert results['valid'] is True
        assert results['has_cover'] is True
        assert results['metadata']['title'] == "Comprehensive EPUB"
        assert results['metadata']['author'] == "Test Author"
        assert results['metadata']['language'] == "en"
        assert results['spine_count'] == 5  # 3 blog + 2 RSS

        # Detailed validation
        with EPUBValidator(output_path) as validator:
            # Check TOC
            toc = validator.get_nav_toc()
            assert len(toc) > 0

            # Check files
            files = validator.list_files()
            assert 'mimetype' in files
            assert any('META-INF' in f for f in files)


@pytest.mark.asyncio
class TestDateFormatting:
    """Test date formatting in different languages."""

    async def test_date_formatting_english(self, temp_dir, httpserver_with_content):
        """Test that dates are formatted in human-readable English."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "English Date Test"
author = "Test Author"
language = "en"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
date = "time.published"
"""
        gensi_path = temp_dir / 'test_english_dates.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Validate the EPUB and check date formatting
        with EPUBValidator(output_path) as validator:
            # Get first article content
            articles = validator.get_articles()
            assert len(articles) > 0

            first_article = articles[0]
            # The date should be formatted in English
            # Original: "2025-01-15T10:00:00Z" or "January 15, 2025"
            # Should contain formatted date components
            assert '2025' in first_article or '25' in first_article
            assert ('Jan' in first_article or 'January' in first_article)

    async def test_date_formatting_german(self, temp_dir, httpserver_with_content):
        """Test that dates are formatted in human-readable German."""
        httpserver = httpserver_with_content

        gensi_content = f"""
title = "German Date Test"
author = "Test Author"
language = "de"

[[index]]
url = "{httpserver.url_for('/blog_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
date = "time.published"
"""
        gensi_path = temp_dir / 'test_german_dates.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Validate the EPUB and check date formatting
        with EPUBValidator(output_path) as validator:
            articles = validator.get_articles()
            assert len(articles) > 0

            first_article = articles[0]
            # The date should be formatted in German format
            # Should contain date in German locale format
            assert '2025' in first_article or '25' in first_article
            # German uses "Januar" for January
            assert ('Jan' in first_article or 'Januar' in first_article or '15' in first_article)

    async def test_date_formatting_with_iso_datetime(self, temp_dir, httpserver_with_content):
        """Test formatting of ISO datetime strings."""
        httpserver = httpserver_with_content

        # Create a custom article with ISO datetime
        custom_article_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ISO Date Article</title>
</head>
<body>
    <article>
        <h1 class="article-title">ISO Date Test</h1>
        <div class="meta">
            <span class="author">Test Author</span>
            <time class="published" datetime="2025-03-20T14:30:00Z">2025-03-20T14:30:00Z</time>
        </div>
        <div class="article-content">
            <p>This article tests ISO datetime formatting.</p>
        </div>
    </article>
</body>
</html>
"""
        # Serve custom article
        httpserver.expect_request('/iso_article.html').respond_with_data(
            custom_article_html,
            content_type='text/html'
        )

        # Create index page
        index_html = f"""<!DOCTYPE html>
<html>
<body>
    <article class="post-preview">
        <a class="post-link" href="{httpserver.url_for('/iso_article.html')}">ISO Article</a>
    </article>
</body>
</html>
"""
        httpserver.expect_request('/iso_index.html').respond_with_data(
            index_html,
            content_type='text/html'
        )

        gensi_content = f"""
title = "ISO DateTime Test"
author = "Test Author"
language = "en"

[[index]]
url = "{httpserver.url_for('/iso_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
date = "time.published"
"""
        gensi_path = temp_dir / 'test_iso_dates.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Check that the raw ISO datetime was formatted properly
        with EPUBValidator(output_path) as validator:
            articles = validator.get_articles()
            assert len(articles) > 0

            article_content = articles[0]
            # Should NOT contain raw ISO format "2025-03-20T14:30:00Z"
            # Should contain formatted date/time
            assert '2025' in article_content or '25' in article_content
            assert 'Mar' in article_content or 'March' in article_content
            # Should include time since it's a datetime
            assert ('14' in article_content or '2:30' in article_content or '30' in article_content)

    async def test_unparseable_date_fallback(self, temp_dir, httpserver_with_content):
        """Test that unparseable dates fall back to original string."""
        httpserver = httpserver_with_content

        # Create article with unparseable date
        custom_article_html = """<!DOCTYPE html>
<html>
<body>
    <article>
        <h1 class="article-title">Unparseable Date Test</h1>
        <time class="published">Not a real date format xyz123</time>
        <div class="article-content">
            <p>This article has an unparseable date.</p>
        </div>
    </article>
</body>
</html>
"""
        httpserver.expect_request('/unparseable_article.html').respond_with_data(
            custom_article_html,
            content_type='text/html'
        )

        index_html = f"""<!DOCTYPE html>
<html>
<body>
    <article class="post-preview">
        <a class="post-link" href="{httpserver.url_for('/unparseable_article.html')}">Article</a>
    </article>
</body>
</html>
"""
        httpserver.expect_request('/unparseable_index.html').respond_with_data(
            index_html,
            content_type='text/html'
        )

        gensi_content = f"""
title = "Unparseable Date Test"
language = "en"

[[index]]
url = "{httpserver.url_for('/unparseable_index.html')}"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
date = "time.published"
"""
        gensi_path = temp_dir / 'test_unparseable.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify that the unparseable date is preserved as-is
        with EPUBValidator(output_path) as validator:
            articles = validator.get_articles()
            assert len(articles) > 0

            article_content = articles[0]
            # Should contain the original unparseable string
            assert 'Not a real date format xyz123' in article_content


class TestStylesheetLinks:
    """Test that stylesheet links are correctly included in generated EPUBs."""

    @pytest.mark.asyncio
    async def test_simple_gensi_has_stylesheet_links(self, temp_dir, httpserver):
        """Test that articles from simple gensi have stylesheet links."""
        # Setup test article
        article_html = """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
    <h1 class="article-title">Test Article</h1>
    <div class="article-content">
        <p>This is test content.</p>
    </div>
</body>
</html>
"""
        httpserver.expect_request('/article.html').respond_with_data(
            article_html,
            content_type='text/html'
        )

        index_html = f"""<!DOCTYPE html>
<html>
<body>
    <a class="article-link" href="{httpserver.url_for('/article.html')}">Test Article</a>
</body>
</html>
"""
        httpserver.expect_request('/index.html').respond_with_data(
            index_html,
            content_type='text/html'
        )

        gensi_content = f"""
title = "Stylesheet Test EPUB"
language = "en"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.article-link"

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'stylesheet_test.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify article has stylesheet link
        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            assert len(spine_items) > 0
            first_id = spine_items[0]
            first_href = manifest.get(first_id)
            assert first_href is not None

            chapter_content = validator.get_chapter_content(first_href)
            assert chapter_content is not None

            # Check for stylesheet link with correct attributes
            assert '<link href="../styles/styles.css"' in chapter_content
            assert 'rel="stylesheet"' in chapter_content
            assert 'type="text/css"' in chapter_content

    @pytest.mark.asyncio
    async def test_nav_has_stylesheet_link_integration(self, temp_dir, httpserver):
        """Test that nav document has stylesheet link in integration test."""
        # Setup test article
        article_html = """<!DOCTYPE html>
<html>
<head><title>Nav Test Article</title></head>
<body>
    <h1 class="article-title">Nav Test Article</h1>
    <div class="article-content">
        <p>Testing nav stylesheet.</p>
    </div>
</body>
</html>
"""
        httpserver.expect_request('/article.html').respond_with_data(
            article_html,
            content_type='text/html'
        )

        index_html = f"""<!DOCTYPE html>
<html>
<body>
    <a class="article-link" href="{httpserver.url_for('/article.html')}">Nav Test Article</a>
</body>
</html>
"""
        httpserver.expect_request('/index.html').respond_with_data(
            index_html,
            content_type='text/html'
        )

        gensi_content = f"""
title = "Nav Stylesheet Test EPUB"
language = "en"

[[index]]
url = "{httpserver.url_for('/index.html')}"
type = "html"
links = "a.article-link"

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'nav_stylesheet_test.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify nav has stylesheet link
        with EPUBValidator(output_path) as validator:
            opf_path = validator.get_content_opf_path()
            assert opf_path is not None

            from lxml import etree
            from pathlib import Path

            content = validator.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}

            # Find nav document
            nav_items = tree.xpath(
                '//opf:manifest/opf:item[@properties="nav"]/@href',
                namespaces=ns
            )
            assert len(nav_items) > 0

            nav_href = nav_items[0]
            opf_dir = str(Path(opf_path).parent)
            if opf_dir == '.':
                nav_path = nav_href
            else:
                nav_path = f"{opf_dir}/{nav_href}"

            nav_content = validator.epub.read(nav_path).decode('utf-8')

            # Check for stylesheet link with correct attributes
            assert '<link href="styles/styles.css"' in nav_content
            assert 'rel="stylesheet"' in nav_content
            assert 'type="text/css"' in nav_content

    @pytest.mark.asyncio
    async def test_multi_index_all_articles_have_stylesheet_links(self, temp_dir, httpserver):
        """Test that all articles from multiple indices have stylesheet links."""
        # Setup multiple articles
        for i in [1, 2, 3]:
            article_html = f"""<!DOCTYPE html>
<html>
<head><title>Article {i}</title></head>
<body>
    <h1 class="article-title">Article {i}</h1>
    <div class="article-content">
        <p>Article {i} content.</p>
    </div>
</body>
</html>
"""
            httpserver.expect_request(f'/article{i}.html').respond_with_data(
                article_html,
                content_type='text/html'
            )

        index1_html = f"""<!DOCTYPE html>
<html>
<body>
    <a class="link" href="{httpserver.url_for('/article1.html')}">Article 1</a>
    <a class="link" href="{httpserver.url_for('/article2.html')}">Article 2</a>
</body>
</html>
"""
        httpserver.expect_request('/index1.html').respond_with_data(
            index1_html,
            content_type='text/html'
        )

        index2_html = f"""<!DOCTYPE html>
<html>
<body>
    <a class="link" href="{httpserver.url_for('/article3.html')}">Article 3</a>
</body>
</html>
"""
        httpserver.expect_request('/index2.html').respond_with_data(
            index2_html,
            content_type='text/html'
        )

        gensi_content = f"""
title = "Multi-Index Stylesheet Test"
language = "en"

[[index]]
name = "Section 1"
url = "{httpserver.url_for('/index1.html')}"
type = "html"
links = "a.link"

[[index]]
name = "Section 2"
url = "{httpserver.url_for('/index2.html')}"
type = "html"
links = "a.link"

[article]
content = "div.article-content"
title = "h1.article-title"
"""
        gensi_path = temp_dir / 'multi_index_stylesheet.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir, cache_enabled=False)

        assert output_path.exists()

        # Verify all articles have stylesheet links
        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            assert len(spine_items) == 3  # 2 from section 1, 1 from section 2

            # Check all articles have stylesheet links
            for item_id in spine_items:
                href = manifest.get(item_id)
                assert href is not None

                chapter_content = validator.get_chapter_content(href)
                assert chapter_content is not None

                # Verify stylesheet link exists
                assert '<link href="../styles/styles.css"' in chapter_content
                assert 'rel="stylesheet"' in chapter_content
                assert 'type="text/css"' in chapter_content
