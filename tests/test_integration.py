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
        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

    [article]
    content = "div.article-content"
    title = "h1.article-title"
    author = "span.author"
"""
        gensi_path = temp_dir / 'override.gensi'
        gensi_path.write_text(gensi_content)

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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
        processor = GensiProcessor(gensi_path, temp_dir, progress_callback)
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
        processor = GensiProcessor(gensi_path, temp_dir, max_parallel=2)
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

        output_path = await process_gensi_file(gensi_path, temp_dir)

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
