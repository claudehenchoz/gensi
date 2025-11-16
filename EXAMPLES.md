# .gensi File Examples

This document provides comprehensive examples of `.gensi` files for various use cases, from simple to advanced configurations.

## Table of Contents

1. [Basic Examples](#basic-examples)
   - [Minimal Configuration](#minimal-configuration)
   - [Simple Blog Archive](#simple-blog-archive)
   - [With Cover Image](#with-cover-image)
2. [RSS/Atom Feed Examples](#rssatom-feed-examples)
   - [Basic RSS Feed](#basic-rss-feed)
   - [RSS with Limit](#rss-with-limit)
   - [RSS with Content Embedded](#rss-with-content-embedded)
   - [Atom Feed](#atom-feed)
3. [Multi-Index EPUBs](#multi-index-epubs)
   - [Multiple HTML Indices](#multiple-html-indices)
   - [Mixed HTML and RSS](#mixed-html-and-rss)
   - [Article Config Override](#article-config-override)
4. [Advanced Extraction](#advanced-extraction)
   - [Element Removal](#element-removal)
   - [Image Control](#image-control)
   - [Complete Metadata](#complete-metadata)
5. [Python Script Examples](#python-script-examples)
   - [Python Index Extraction](#python-index-extraction)
   - [Python Article Extraction](#python-article-extraction)
   - [RSS Filtering with Python](#rss-filtering-with-python)
   - [Complex Python Logic](#complex-python-logic)
6. [Real-World Examples](#real-world-examples)
   - [Online Magazine](#online-magazine)
   - [Blog with Images](#blog-with-images)
   - [Newsletter Archive](#newsletter-archive)

---

## Basic Examples

### Minimal Configuration

The simplest possible `.gensi` file requires only a title, one index, and article extraction rules.

```toml
# Minimal configuration
# Only required fields: title, one [[index]] section, and [article] section

title = "My First EPUB"

# Define where to find the list of articles
[[index]]
url = "https://example.com/blog/archive"
type = "html"  # Type can be "html" or "rss"
links = "article.post a"  # CSS selector for article links

# Define how to extract article content
[article]
content = "div.article-body"  # CSS selector for main content
```

**When to use:** Quick EPUB generation from a simple blog or website with consistent structure.

---

### Simple Blog Archive

A more complete example with metadata and multiple extraction fields.

```toml
# Basic blog EPUB with metadata
# Includes: title, author, language, and article metadata extraction

title = "Example Blog Collection"
author = "Blog Author"  # Optional: will be used as EPUB author
language = "en"  # Optional: language code (default: "en")

[[index]]
url = "https://example.com/blog/archive"
type = "html"
links = "article.post-preview a.post-link"

[article]
# Main content selector (required)
content = "div.post-content"

# Optional metadata selectors
# These will fall back to HTML meta tags if not found
title = "h1.post-title"  # Extract article title
author = "span.author-name"  # Extract article author
date = "time.published"  # Extract publication date
```

**When to use:** Standard blog scraping where you want to preserve article metadata (title, author, date).

---

### With Cover Image

Add a cover image to your EPUB by specifying either a direct image URL or a page with an image to extract.

```toml
title = "Blog with Cover"
author = "Author Name"

# Cover image configuration
[cover]
# Option 1: Direct URL to an image file
url = "https://example.com/images/cover.jpg"

# Option 2: Extract image from a page using CSS selector
# url = "https://example.com"
# selector = "img.site-logo"  # CSS selector for the cover image

[[index]]
url = "https://example.com/blog"
type = "html"
links = "article a.read-more"

[article]
content = "div.article-content"
title = "h1.title"
```

**When to use:**
- **Direct URL:** When you have a direct link to a cover image file
- **Selector:** When the cover image is embedded in a webpage (e.g., site logo, featured image)

---

## RSS/Atom Feed Examples

### Basic RSS Feed

Process articles from an RSS or Atom feed. Gensi will fetch each article URL from the feed.

```toml
title = "RSS Feed EPUB"
author = "Feed Author"

[[index]]
url = "https://example.com/feed.xml"
type = "rss"  # Use "rss" for both RSS and Atom feeds

# When fetching from RSS, gensi will:
# 1. Parse the RSS/Atom feed
# 2. Extract article URLs from feed entries
# 3. Fetch each article URL
# 4. Extract content using the [article] rules below

[article]
content = "div.article-content"
title = "h1.article-title"
```

**When to use:** Converting RSS/Atom feed content to EPUB, fetching full articles from their URLs.

---

### RSS with Limit

Limit the number of articles from an RSS feed (useful for large feeds or testing).

```toml
title = "Latest 10 Articles"

[[index]]
url = "https://example.com/feed.xml"
type = "rss"
limit = 10  # Only process the first 10 entries from the feed

[article]
content = "div.post-content"
```

**When to use:**
- Processing only recent articles from a frequently updated feed
- Testing your configuration on a subset before processing the full feed
- Creating "Best of" collections with a specific number of entries

---

### RSS with Content Embedded

Use content directly from the RSS feed instead of fetching article URLs (faster, but may have incomplete content).

```toml
title = "RSS Content EPUB"

[[index]]
url = "https://example.com/feed.xml"
type = "rss"
use_content_encoded = true  # Use content from <content:encoded> or <content> tags
limit = 20

# When use_content_encoded = true:
# - Content is taken directly from the feed
# - Article URLs are NOT fetched
# - [article] section is NOT used for extraction
# - Useful when feed contains full article HTML
# - Much faster (no additional HTTP requests)
```

**When to use:**
- Feed contains complete article HTML in `<content:encoded>` or `<content>` tags
- Want faster processing (no individual article fetching)
- Feed content is sufficient for your needs

**Note:** When `use_content_encoded = true`, the `[article]` section is not used.

---

### Atom Feed

Atom feeds work the same way as RSS feeds (just use `type = "rss"`).

```toml
title = "Atom Feed EPUB"
author = "Author"

[[index]]
url = "https://example.com/atom.xml"  # Can be either RSS or Atom
type = "rss"  # Use "rss" for both RSS 2.0 and Atom feeds

[article]
content = "article.post-body"
title = "h1.entry-title"
```

**When to use:** Processing Atom feeds (Gensi auto-detects RSS vs Atom format).

---

## Multi-Index EPUBs

### Multiple HTML Indices

Create an EPUB with multiple sections, each from a different source.

```toml
title = "Multi-Section EPUB"
author = "Various Authors"

# When you have multiple [[index]] sections, each MUST have a "name"
# The name becomes the section title in the EPUB table of contents

[[index]]
name = "Blog Posts"  # Required when using multiple indices
url = "https://example.com/blog/archive"
type = "html"
links = "article.post a"

[[index]]
name = "Tutorials"  # Each section gets its own name
url = "https://example.com/tutorials"
type = "html"
links = "div.tutorial-list a.tutorial-link"

# Shared article extraction rules apply to all indices
[article]
content = "div.content"
title = "h1.title"
```

**When to use:**
- Combining content from multiple pages or sites
- Organizing EPUB into logical sections
- Creating themed collections from different sources

**EPUB Structure:**
```
├─ Blog Posts
│  ├─ Article 1
│  ├─ Article 2
│  └─ Article 3
└─ Tutorials
   ├─ Tutorial 1
   └─ Tutorial 2
```

---

### Mixed HTML and RSS

Combine HTML archive pages and RSS feeds in a single EPUB.

```toml
title = "Mixed Content EPUB"
author = "Multiple Sources"

[[index]]
name = "Web Articles"
url = "https://example.com/articles"
type = "html"
links = "article a.read-more"

[[index]]
name = "Latest from RSS"
url = "https://example.com/rss"
type = "rss"
limit = 5  # Only 5 most recent from RSS

[article]
content = "div.article-content"
title = "h1"
author = "span.byline"
```

**When to use:**
- Combining static archives with dynamic RSS feeds
- Mixing different content types in one EPUB
- Creating comprehensive collections from multiple sources

---

### Article Config Override

Override article extraction rules for specific indices (useful when different sections have different HTML structures).

```toml
title = "Override Example"
author = "Author"

# Global article configuration (default for all indices)
[article]
content = "div.article-content"
title = "h1.article-title"

[[index]]
name = "Section 1"
url = "https://example.com/section1"
type = "html"
links = "article a"
# Uses global [article] config above

[[index]]
name = "Section 2"
url = "https://example.com/section2"
type = "html"
links = "div.post a"

# Override article config ONLY for "Section 2"
# This section uses different CSS selectors
[index.article]
content = "div.post-body"  # Different content selector
title = "h2.post-title"  # Different title selector
author = "span.author"  # Additional field not in global config
```

**When to use:**
- Different sections of your EPUB have different HTML structures
- One source needs additional metadata fields
- Per-section customization of extraction rules

**Important:** `[index.article]` applies ONLY to the `[[index]]` section immediately before it.

---

## Advanced Extraction

### Element Removal

Remove unwanted elements from article content (ads, sidebars, comments, share buttons, etc.).

```toml
title = "Clean Content EPUB"

[[index]]
url = "https://example.com/blog"
type = "html"
links = "article a.permalink"

[article]
content = "div.post-content"
title = "h1.post-title"

# Remove unwanted elements using CSS selectors
# These elements will be removed from the article content BEFORE saving
remove = [
    ".sidebar",           # Sidebar content
    ".comments",          # Comment sections
    ".share-buttons",     # Social media buttons
    ".advertisement",     # Ads
    "div.related-posts",  # Related posts widgets
    "script",             # JavaScript tags
    "style"               # Inline style tags
]
```

**When to use:**
- Removing ads, sidebars, or other clutter from articles
- Cleaning up content for better reading experience
- Stripping tracking scripts, share buttons, or social media widgets

**How it works:** Elements matching these selectors are removed from the article DOM before converting to EPUB.

---

### Image Control

Control whether images are included in the EPUB (enabled by default).

```toml
title = "Image Control Example"

[[index]]
url = "https://example.com/articles"
type = "html"
links = "article a"

[article]
content = "div.article-body"

# Image handling options:

# Option 1: Include images (default behavior)
images = true
# - Downloads all images from articles
# - Embeds them in the EPUB
# - Updates <img> tags to reference embedded images

# Option 2: Remove images
# images = false
# - Removes all <img> tags from content
# - Creates a text-only EPUB
# - Useful for: reducing file size, text-only readers, or image-heavy content
```

**When to use:**
- **`images = true`** (default): Normal behavior, includes illustrations, diagrams, photos
- **`images = false`**: Text-only EPUBs, bandwidth constraints, or when images aren't important

**Performance Note:** Disabling images significantly reduces:
- EPUB file size
- Processing time
- Network bandwidth usage

---

### Complete Metadata

Extract all available metadata fields for comprehensive article information.

```toml
title = "Complete Metadata EPUB"
author = "Publisher Name"
language = "en"

# Optional: Add publisher information
# publisher = "Publisher Name"

[[index]]
url = "https://example.com/archive"
type = "html"
links = "article a.article-link"

[article]
# Required: Main content
content = "div.article-content"

# Optional: All metadata fields
title = "h1.article-title"      # Article title
author = "span.article-author"  # Article author
date = "time.published"         # Publication date

# When using <time> elements, gensi will:
# - First try to extract text content (e.g., "January 15, 2025")
# - Fall back to the "datetime" attribute if text is empty

# Metadata fallback behavior:
# If CSS selectors don't find metadata, gensi automatically checks:
# - <meta property="og:title"> (Open Graph)
# - <meta name="twitter:title"> (Twitter Cards)
# - <meta property="article:author">
# - <meta property="article:published_time">
# - <title> tag (for title fallback)

# Remove unwanted elements
remove = [
    ".sidebar",
    ".comments",
    "div.advertisement"
]

# Control images
images = true
```

**When to use:** When you want comprehensive article information preserved in your EPUB.

---

## Python Script Examples

Python scripts provide unlimited flexibility when CSS selectors aren't sufficient.

### Python Index Extraction

Use Python for complex index extraction logic (filtering, custom URL building, etc.).

```toml
title = "Python Index EPUB"

[[index]]
url = "https://example.com/archive"
type = "html"

# Python script for index extraction
# Replaces the "links" CSS selector with custom logic
[index.python]
script = '''
# The "document" variable is available (lxml HTML element)
# Must return: list of dicts with "url" key
# Optional: "content" key for pre-fetched content

articles = []
for elem in document.cssselect('article.post-preview a.post-link'):
    url = elem.get('href')
    articles.append({'url': url})
return articles
'''

[article]
content = "div.article-content"
title = "h1.article-title"
```

**When to use:**
- Links require complex URL manipulation
- Need to filter links based on attributes or content
- Links are generated dynamically or need custom logic
- CSS selectors alone can't express the extraction logic

**Available variables:** `document` (lxml HTML element)

**Return format:** `[{'url': 'article_url'}, {'url': 'article_url2'}, ...]`

---

### Python Article Extraction

Use Python for complex article extraction (multiple content sections, conditional logic, etc.).

```toml
title = "Python Article EPUB"

[[index]]
url = "https://example.com/blog"
type = "html"
links = "article a"

# Python script for article extraction
# Replaces CSS selectors with custom logic
[article.python]
script = '''
from lxml import etree

# The "document" variable is available (lxml HTML element)
# Can return either:
# 1. String: HTML content only (metadata from fallback)
# 2. Dict: Must have "content" key, optional "title", "author", "date"

content_div = document.cssselect('div.article-content')[0]
title_elem = document.cssselect('h1.article-title')

# Return a dictionary with content and metadata
return {
    'content': etree.tostring(content_div, encoding='unicode'),
    'title': title_elem[0].text if title_elem else None
}

# Alternative: Return just the content string
# return etree.tostring(content_div, encoding='unicode')
'''
```

**When to use:**
- Article content is split across multiple elements
- Need conditional logic (e.g., different structures for different article types)
- Complex HTML manipulation required
- CSS selectors can't express the extraction logic

**Available variables:** `document` (lxml HTML element)

**Return formats:**
1. **String:** HTML content only (title/author/date use metadata fallback)
2. **Dict:** `{'content': 'html', 'title': '...', 'author': '...', 'date': '...'}`

---

### RSS Filtering with Python

Filter and customize RSS feed entries using Python logic.

```toml
title = "Filtered RSS EPUB"

[[index]]
url = "https://example.com/feed.xml"
type = "rss"

# Python script for RSS filtering
[index.python]
script = '''
# The "feed" variable is available (feedparser result)
# Must return: list of dicts with "url" key
# Optional: "content" key for embedded content

articles = []
for entry in feed.entries:
    # Filter by categories/tags
    categories = [cat.get('term', '') for cat in entry.get('tags', [])]

    # Only include articles tagged "Technology" but not "Sponsored"
    if 'Technology' in categories and 'Sponsored' not in categories:
        articles.append({'url': entry.link})

return articles
'''

[article]
content = "div.article-content"
```

**When to use:**
- Filtering RSS entries by category, tag, date, or other criteria
- Cherry-picking specific entries from a feed
- Excluding sponsored or promotional content
- Custom RSS entry selection logic

**Available variables:** `feed` (feedparser parsed feed object)

**Feed entry attributes:**
- `entry.link` - Article URL
- `entry.title` - Entry title
- `entry.get('tags', [])` - Categories/tags
- `entry.get('published_parsed')` - Publication date
- `entry.get('author')` - Author
- See [feedparser documentation](https://feedparser.readthedocs.io/) for more

---

### Complex Python Logic

Advanced Python example combining multiple techniques.

```toml
title = "Advanced Python EPUB"

[[index]]
url = "https://example.com/archive"
type = "html"

[index.python]
script = '''
# Complex index extraction with filtering and URL manipulation

articles = []
for elem in document.cssselect('article.post'):
    # Get the link
    link = elem.cssselect('a.post-link')[0]
    url = link.get('href')

    # Skip if URL contains certain patterns
    if '/sponsored/' in url or '/ad-' in url:
        continue

    # Only include posts with "Featured" badge
    badges = elem.cssselect('.badge')
    if any('Featured' in badge.text for badge in badges if badge.text):
        # Make URL absolute if needed
        if url.startswith('/'):
            url = 'https://example.com' + url

        articles.append({'url': url})

return articles
'''

[article.python]
script = '''
from lxml import etree

# Extract main content
content_parts = []
for section in document.cssselect('div.article-section'):
    # Skip advertisement sections
    if 'advertisement' in section.get('class', ''):
        continue
    content_parts.append(etree.tostring(section, encoding='unicode'))

# Combine all parts
full_content = ''.join(content_parts)

# Extract metadata with fallbacks
title_elem = document.cssselect('h1.title')
title = title_elem[0].text if title_elem else document.cssselect('title')[0].text

author_elem = document.cssselect('span.author')
author = author_elem[0].text if author_elem else None

return {
    'content': full_content,
    'title': title,
    'author': author
}
'''
```

**When to use:**
- Complex extraction requirements beyond CSS selectors
- Multiple content sections need to be combined
- Conditional logic based on article attributes
- URL manipulation or filtering
- Advanced HTML processing needs

---

## Real-World Examples

### Online Magazine

Complete example for scraping an online magazine (based on Clarkesworld Magazine).

```toml
# Real-world magazine EPUB configuration
# Based on Clarkesworld Magazine structure

title = "Clarkesworld Magazine 229 - October 2025"
author = "Clarkesworld"
language = "en"

# Direct URL to cover image
[cover]
url = "https://clarkesworldmagazine.com/covers/cw_229_800.jpg"

# Magazine issue table of contents page
[[index]]
url = "https://clarkesworldmagazine.com/prior/issue_229/"
type = "html"
# Complex nested selector for story links in the issue index
links = "div.issue-index div.index-table div.index-table div p.story a"

[article]
# Main story text container
content = "div.content-section div.story-text"

# Metadata selectors
title = "div.content-section h1"
author = "span.authorname"

# Remove magazine-specific elements that shouldn't be in EPUB
remove = [
    "p.issue-heading",       # Issue number heading
    "p.story-description",   # Story description (duplicates content)
    "p.audio-text",          # Audio version links
    "div.aboutinfo",         # Author bio boxes
    "div.addtoany_content",  # Social sharing buttons
    "h3.about",              # "About the author" headings
    "div.molongui-clearfix"  # Layout div elements
]
```

**Use case:** Scraping professionally published online magazines with complex layouts.

---

### Blog with Images

Blog EPUB with complete metadata and image handling.

```toml
title = "Tech Blog Collection"
author = "Tech Blogger"
language = "en"

# Extract logo as cover from homepage
[cover]
url = "https://techblog.example.com"
selector = "img.site-logo"

[[index]]
url = "https://techblog.example.com/archive"
type = "html"
links = "article.post-card a.post-link"

[article]
# Main content area
content = "div.post-content"

# Metadata extraction
title = "h1.post-title"
author = "a.author-link"
date = "time.post-date"

# Clean up the content
remove = [
    "div.post-sidebar",      # Sidebar content
    "div.share-buttons",     # Social sharing
    "div.related-posts",     # Related posts widget
    "div.comments-section",  # Comments
    ".advertisement",        # Ads
    "div.newsletter-signup"  # Newsletter signup forms
]

# Include images (screenshots, diagrams, etc.)
images = true
```

**Use case:** Technical blogs with code examples, diagrams, and screenshots.

---

### Newsletter Archive

RSS-based newsletter EPUB with embedded content.

```toml
title = "Weekly Newsletter - Best Of 2025"
author = "Newsletter Author"
language = "en"

# Newsletter RSS feed
[[index]]
url = "https://newsletter.example.com/feed"
type = "rss"

# Use content directly from RSS (newsletters usually include full HTML)
use_content_encoded = true

# Only get issues from 2025 (adjust limit based on your needs)
limit = 52  # Approximately one year of weekly newsletters

# Note: When use_content_encoded = true, the [article] section
# is not needed since content comes from the feed itself
```

**Use case:** Creating EPUB archives of email newsletters that publish full content in their RSS feeds.

---

## Tips and Best Practices

### CSS Selector Tips

1. **Use specific selectors:** `div.article-content` is better than just `div`
2. **Inspect the HTML:** Use browser DevTools to find the right selectors
3. **Test selectors:** Use browser console: `document.querySelectorAll('your-selector')`
4. **Be consistent:** Look for selectors that work across all articles

### Python Script Tips

1. **Keep it simple:** Use CSS selectors when possible, Python when necessary
2. **Test incrementally:** Build scripts step-by-step
3. **Handle errors:** Check if elements exist before accessing them
4. **Return correct format:** Verify your return value matches the expected format

### Performance Tips

1. **Use `limit`:** Test with small numbers before processing full feeds
2. **Disable images:** Set `images = false` for faster processing and smaller files
3. **Use `use_content_encoded`:** Skip article fetching when RSS has full content
4. **Parallel processing:** Use CLI `--parallel` option for multiple files

### Debugging Tips

1. **Start simple:** Begin with minimal config, add complexity gradually
2. **Check one article:** Process a single article first to verify extraction
3. **Validate EPUB:** Use `epubcheck` to validate generated EPUBs
4. **Check selectors:** Ensure CSS selectors match the actual HTML structure

---

## Command-Line Usage

Process your `.gensi` files:

```bash
# Single file
uv run gensi process magazine.gensi

# Multiple files
uv run gensi process *.gensi

# With options
uv run gensi process blog.gensi --output-dir ./epubs --parallel 5 --verbose

# GUI mode
uv run gensi-gui
```

For more information, see the main README.md file.
