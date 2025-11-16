"""Shared fixtures for gensi tests."""

import pytest
from pathlib import Path
from pytest_httpserver import HTTPServer
import tempfile
import shutil


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--epub-output",
        action="store",
        default=None,
        help="Directory to save generated EPUB files from tests"
    )


@pytest.fixture
def fixtures_dir():
    """Return the fixtures directory path."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def html_fixtures_dir(fixtures_dir):
    """Return the HTML fixtures directory path."""
    return fixtures_dir / 'html'


@pytest.fixture
def rss_fixtures_dir(fixtures_dir):
    """Return the RSS fixtures directory path."""
    return fixtures_dir / 'rss'


@pytest.fixture
def images_fixtures_dir(fixtures_dir):
    """Return the images fixtures directory path."""
    return fixtures_dir / 'images'


@pytest.fixture
def gensi_fixtures_dir(fixtures_dir):
    """Return the gensi fixtures directory path."""
    return fixtures_dir / 'gensi'


@pytest.fixture
def epub_output_dir(request):
    """Get the EPUB output directory from command line option."""
    output_dir = request.config.getoption("--epub-output")
    if output_dir:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return None


@pytest.fixture
def epub_saver(request, epub_output_dir):
    """
    Fixture to save EPUBs from tests.

    Returns a callable that can be used to save an EPUB file with a test-specific name.
    """
    def save_epub(epub_path: Path, custom_name: str = None):
        """Save an EPUB file to the output directory if specified."""
        if not epub_output_dir or not epub_path or not epub_path.exists():
            return

        # Generate a name based on the test if custom name not provided
        if custom_name:
            output_name = custom_name
        else:
            # Use test name as the filename
            test_name = request.node.name
            # Clean up the test name to make it filesystem-friendly
            output_name = test_name.replace('[', '_').replace(']', '').replace('::', '_')

        # Ensure it ends with .epub
        if not output_name.endswith('.epub'):
            output_name += '.epub'

        output_path = epub_output_dir / output_name
        shutil.copy2(epub_path, output_path)
        print(f"\nSaved EPUB: {output_path}")

    return save_epub


@pytest.fixture
def temp_dir(epub_saver):
    """Create a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path

    # Before cleanup, save any EPUB files if output directory is specified
    for epub_file in temp_path.glob('*.epub'):
        epub_saver(epub_file)

    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def httpserver_with_content(httpserver: HTTPServer, html_fixtures_dir, rss_fixtures_dir, images_fixtures_dir):
    """
    Configure HTTP server with test content.

    Serves:
    - HTML files from /fixtures/html/
    - RSS files from /fixtures/rss/
    - Images from /images/
    """
    # Serve HTML files
    for html_file in html_fixtures_dir.glob('*.html'):
        content = html_file.read_text(encoding='utf-8')
        httpserver.expect_request(f'/{html_file.name}').respond_with_data(
            content,
            content_type='text/html'
        )

    # Serve RSS files
    for rss_file in rss_fixtures_dir.glob('*.xml'):
        content = rss_file.read_text(encoding='utf-8')
        httpserver.expect_request(f'/{rss_file.name}').respond_with_data(
            content,
            content_type='application/xml'
        )

    # Serve images
    for image_file in images_fixtures_dir.glob('*'):
        if image_file.is_file():
            content = image_file.read_bytes()
            # Determine content type
            suffix = image_file.suffix.lower()
            if suffix == '.jpg' or suffix == '.jpeg':
                content_type = 'image/jpeg'
            elif suffix == '.png':
                content_type = 'image/png'
            elif suffix == '.gif':
                content_type = 'image/gif'
            elif suffix == '.webp':
                content_type = 'image/webp'
            else:
                content_type = 'application/octet-stream'

            httpserver.expect_request(f'/images/{image_file.name}').respond_with_data(
                content,
                content_type=content_type
            )

    return httpserver


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="author" content="Test Author">
    <meta property="article:published_time" content="2025-01-15T10:00:00Z">
</head>
<body>
    <article>
        <h1 class="title">Test Article</h1>
        <div class="content">
            <p>This is test content.</p>
        </div>
    </article>
</body>
</html>
"""


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title>Test Feed</title>
        <link>http://example.com</link>
        <item>
            <title>Test Item</title>
            <link>http://example.com/item1</link>
            <description>Test description</description>
            <content:encoded><![CDATA[<p>Test content</p>]]></content:encoded>
        </item>
    </channel>
</rss>
"""


@pytest.fixture
def progress_callback():
    """Mock progress callback that stores progress updates."""
    class ProgressTracker:
        def __init__(self):
            self.updates = []

        def __call__(self, progress):
            self.updates.append({
                'stage': progress.stage,
                'current': progress.current,
                'total': progress.total,
                'message': progress.message
            })

    return ProgressTracker()


@pytest.fixture
def valid_gensi_simple(temp_dir):
    """Create a valid simple .gensi file for testing."""
    content = """
title = "Test EPUB"
author = "Test Author"
language = "en"

[[index]]
url = "http://localhost/blog_index.html"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
author = "span.author"
date = "time.published"
remove = [".sidebar"]
"""
    gensi_path = temp_dir / 'test.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def valid_gensi_with_cover(temp_dir):
    """Create a valid .gensi file with cover for testing."""
    content = """
title = "Test EPUB with Cover"
author = "Test Author"
language = "en"

[cover]
url = "http://localhost/cover_page.html"
selector = "img.site-logo"

[[index]]
url = "http://localhost/blog_index.html"
type = "html"
links = "article.post-preview a.post-link"

[article]
content = "div.article-content"
title = "h1.article-title"
"""
    gensi_path = temp_dir / 'test_with_cover.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def valid_gensi_multi_index(temp_dir):
    """Create a valid .gensi file with multiple indices for testing."""
    content = """
title = "Multi-Index EPUB"
author = "Test Author"
language = "en"

[[index]]
name = "Blog Posts"
url = "http://localhost/blog_index.html"
type = "html"
links = "article.post-preview a.post-link"

[[index]]
name = "RSS Feed"
url = "http://localhost/test_feed_rss.xml"
type = "rss"
limit = 2

[article]
content = "div.article-content"
title = "h1.article-title"
"""
    gensi_path = temp_dir / 'multi_index.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def valid_gensi_with_python(temp_dir):
    """Create a valid .gensi file with Python scripts for testing."""
    content = """
title = "Python Script EPUB"
author = "Test Author"

[[index]]
url = "http://localhost/blog_index.html"
type = "html"

[index.python]
script = '''
articles = []
for elem in document.cssselect('article.post-preview a.post-link'):
    articles.append({'url': elem.get('href')})
return articles
'''

[article]
content = "div.article-content"
title = "h1.article-title"
"""
    gensi_path = temp_dir / 'with_python.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def invalid_gensi_no_title(temp_dir):
    """Create an invalid .gensi file (missing title) for testing."""
    content = """
author = "Test Author"

[[index]]
url = "http://localhost/blog_index.html"
type = "html"
links = "article.post-preview a.post-link"
"""
    gensi_path = temp_dir / 'invalid_no_title.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def invalid_gensi_no_index(temp_dir):
    """Create an invalid .gensi file (missing index) for testing."""
    content = """
title = "Test EPUB"
author = "Test Author"
"""
    gensi_path = temp_dir / 'invalid_no_index.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def invalid_gensi_wrong_type(temp_dir):
    """Create an invalid .gensi file (wrong type value) for testing."""
    content = """
title = "Test EPUB"

[[index]]
url = "http://localhost/blog_index.html"
type = "invalid_type"
links = "a"
"""
    gensi_path = temp_dir / 'invalid_type.gensi'
    gensi_path.write_text(content)
    return gensi_path


@pytest.fixture
def invalid_gensi_multi_no_name(temp_dir):
    """Create an invalid .gensi file (multiple indices without name) for testing."""
    content = """
title = "Test EPUB"

[[index]]
url = "http://localhost/index1.html"
type = "html"
links = "a"

[[index]]
url = "http://localhost/index2.html"
type = "html"
links = "a"
"""
    gensi_path = temp_dir / 'invalid_multi_no_name.gensi'
    gensi_path.write_text(content)
    return gensi_path
