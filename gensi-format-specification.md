# .gensi Format Specification

## Version 1.0

## Overview

The `.gensi` format is a TOML-based recipe format for generating EPUB files from web sources. It follows a "simple by default, powerful when needed" philosophy, allowing users to configure most tasks with simple strings (URLs, CSS selectors) while providing Python script overrides for complex logic.

## File Format

- **Base Format**: TOML (Tom's Obvious Minimal Language)
- **File Extension**: `.gensi`
- **Encoding**: UTF-8

## Core Principles

1. **Simple by Default**: Most fields accept simple string values (URLs, CSS selectors)
2. **Python Override System**: Nearly every configuration section can be replaced with a `[section.python]` table containing a script
3. **Context-Based Execution**: Python scripts execute with specific context variables and must return specific types
4. **Override Precedence**: When a `[section.python]` table exists, it supersedes the simple field configurations

## Top-Level Structure

```toml
# Global metadata (required/optional)
title = "string"
author = "string"
language = "string"

# Cover image (optional)
[cover]

# Article index sources (required, repeatable)
[[index]]

# Default article extraction rules (optional)
[article]
```

---

## 1. Global Metadata

These top-level keys define the EPUB metadata.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | String | **Yes** | The title of the generated EPUB file |
| `author` | String | No | The author of the EPUB |
| `language` | String | No | IETF language code (e.g., "en", "fr-CA", "ja") |

### Example

```toml
title = "My Ebook Title"
author = "Recipe Author"
language = "en"
```

---

## 2. Cover Image `[cover]`

Optional section defining how to obtain the ebook's cover image.

### Simple Mode Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | String | **Yes** | URL of a page containing the cover image OR direct URL to an image file |
| `selector` | String | No | CSS selector to find the `<img>` tag. The `src` attribute will be extracted. Ignored if `url` points directly to an image file. |

### Complex Mode: `[cover.python]`

When this section exists, all simple mode fields except `url` are ignored.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `script` | String | **Yes** | Python script to execute |

**Python Context:**
- `document`: BeautifulSoup/lxml parsed object of the page at `cover.url`

**Must Return:** String (direct URL to the cover image)

### Example (Simple)

```toml
[cover]
url = "https://my-blog.com/about"
selector = "img.profile-picture"
```

### Example (Complex)

```toml
[cover]
url = "https://my-blog.com/"

[cover.python]
script = """
hero_div = document.select_one("div.hero-banner")
style = hero_div["style"]
img_url = style.split("'")[1]
return img_url
"""
```

### Implementation Notes

- The tool must resolve relative URLs to absolute URLs
- When `url` points directly to an image file (e.g., `.jpg`, `.png`, `.gif`, `.webp`), the `selector` field is ignored
- The image URL returned by Python scripts should be made absolute by the implementation

---

## 3. Article Index `[[index]]`

Required, repeatable section defining how to find the list of article URLs (chapters).

**Important:** This is an **array of tables** in TOML (denoted by double brackets `[[index]]`). Multiple `[[index]]` blocks can be defined to merge sources. Articles are added to the EPUB in the order the `[[index]]` blocks appear.

### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | **Yes** | Name of this index/section. Used to group articles in the EPUB table of contents. |
| `url` | String | **Yes** | URL of the index page or RSS/Atom feed |
| `type` | String | **Yes** | Type of source. Valid values: `"html"` or `"rss"` |

### Type-Specific Configuration

The remaining configuration depends on the `type` field value.

---

### 3a. Index Type: `"html"`

Used when scraping an HTML page for article links.

#### Simple Mode Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | String | **Yes** | CSS selector for the container of each article in the list |
| `link` | String | **Yes** | CSS selector (relative to each item) to find the article's link. The `href` attribute will be extracted. |

#### Complex Mode: `[index.python]`

When this section exists, all simple mode fields are ignored.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `script` | String | **Yes** | Python script to execute |

**Python Context:**
- `document`: BeautifulSoup/lxml parsed object of the page at `index.url`

**Must Return:** List of dictionaries, where each dictionary has:
- `"url"` (string, **required**): Article URL
- `"content"` (string, optional): HTML content. If provided, the `[article]` processing step is skipped for this item.

#### Example (Simple)

```toml
[[index]]
name = "Blog Archives"
url = "https://my-blog.com/archive"
type = "html"
items = "article.post-preview"
link = "a.read-more-link"
```

#### Example (Complex)

```toml
[[index]]
name = "Blog Archives"
url = "https://my-blog.com/archive"
type = "html"

[index.python]
script = """
articles = []
for item in document.select("article.post-preview"):
    if "external-link" in item.get("class", []):
        continue
    
    link_elem = item.select_one("a.read-more-link")
    
    if link_elem:
        articles.append({
            "url": link_elem["href"]
        })
return articles
"""
```

---

### 3b. Index Type: `"rss"`

Used when consuming an RSS or Atom feed.

#### Simple Mode Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `limit` | Integer | No | Limit the number of entries from the feed |
| `use_content_encoded` | Boolean | No | If `true`, use the entry's content (e.g., `<content:encoded>`) as the chapter body and skip the `[article]` step. Default: `false` |

#### Complex Mode: `[index.python]`

When this section exists, all simple mode fields are ignored.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `script` | String | **Yes** | Python script to execute |

**Python Context:**
- `feed`: Parsed feed object (e.g., from feedparser library)
  - `feed.entries`: List of entry objects

**Must Return:** List of dictionaries, where each dictionary has:
- `"url"` (string, **required**): Article URL
- `"content"` (string, optional): HTML content. If provided, the `[article]` processing step is skipped for this item.

#### Example (Simple)

```toml
[[index]]
name = "News Feed"
url = "https://example.com/feed.rss"
type = "rss"
limit = 10
use_content_encoded = false
```

#### Example (Complex)

```toml
[[index]]
name = "Technology News"
url = "https://example.com/news.rss"
type = "rss"

[index.python]
script = """
articles = []
for entry in feed.entries:
    tags = [tag.term for tag in entry.get("tags", [])]
    if "must-read" in tags:
        content_html = ""
        if hasattr(entry, "content"):
            content_html = entry.content[0].value
        
        articles.append({
            "url": entry.link,
            "content": content_html
        })
return articles
"""
```

---

## 4. Article Content `[article]`

Defines how to extract the main content and metadata from each article's URL.

### Scope and Overrides

1. **Global Default**: A top-level `[article]` section defines default rules for all articles from all indices
2. **Per-Index Override**: An `[article]` table nested inside an `[[index]]` block overrides the global rules for that index only
3. **Skip Condition**: This step is skipped for any article where the `[index.python]` script provided a `"content"` key

### Simple Mode Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | String | **Yes** | CSS selector for the main article content block |
| `title` | String | No | CSS selector for the article title. If not provided, the implementation should fall back to HTML metadata tags (e.g., `<title>`, `og:title`, `twitter:title`) |
| `author` | String | No | CSS selector for the article author. If not provided, the implementation should fall back to HTML metadata tags (e.g., `<meta name="author">`, `article:author`) |
| `date` | String | No | CSS selector for the publication date. If not provided, the implementation should fall back to HTML metadata tags (e.g., `<meta property="article:published_time">`, `<time>` elements) |
| `remove` | Array of Strings | No | List of CSS selectors to remove from the extracted content |

### Metadata Fallback Logic

When metadata fields (`title`, `author`, `date`) are not provided or the selectors don't match, the implementation should attempt to extract metadata from common HTML meta tags in the following order:

**Title Fallback:**
1. `<meta property="og:title">`
2. `<meta name="twitter:title">`
3. `<title>` tag
4. `<h1>` tag (first occurrence)

**Author Fallback:**
1. `<meta name="author">`
2. `<meta property="article:author">`
3. `<meta property="og:article:author">`
4. `<span class="author">`, `<div class="author">`, or similar common patterns

**Date Fallback:**
1. `<meta property="article:published_time">`
2. `<meta property="og:article:published_time">`
3. `<time datetime="...">` attribute
4. `<meta name="date">`
5. `<meta name="pubdate">`

### Complex Mode: `[article.python]`

When this section exists, all simple mode fields are ignored.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `script` | String | **Yes** | Python script to execute |

**Python Context:**
- `document`: BeautifulSoup/lxml parsed object of the article page

**Must Return:** Either:
1. **String**: The final, cleaned HTML for the chapter. Metadata will be extracted using fallback logic.
2. **Dictionary** with the following keys:
   - `"content"` (string, **required**): The final, cleaned HTML for the chapter
   - `"title"` (string, optional): Article title
   - `"author"` (string, optional): Article author
   - `"date"` (string, optional): Publication date (ISO 8601 format recommended)

### Example (Simple, Global)

```toml
[article]
content = "div.article-body"
title = "h1.article-title"
author = "span.author-name"
date = "time.published-date"
remove = [
    "div.advertisement",
    ".social-share-buttons",
    "#comments"
]
```

### Example (Complex, Global)

```toml
[article.python]
script = """
main_content = document.select_one("main.post-content")

if main_content:
    for el in main_content.select("script, style, .ad-slot"):
        el.decompose()
    
    for img in main_content.select("img[data-src]"):
        img["src"] = img["data-src"]
        del img["data-src"]
    
    # Extract metadata
    title_elem = document.select_one("h1.post-title")
    author_elem = document.select_one("span.author")
    date_elem = document.select_one("time.published")
    
    return {
        "content": str(main_content),
        "title": title_elem.text.strip() if title_elem else None,
        "author": author_elem.text.strip() if author_elem else None,
        "date": date_elem.get("datetime") if date_elem else None
    }
else:
    return "<p>Error: Could not find article content.</p>"
"""
```

### Example (Per-Index Override)

```toml
# Global default
[article]
content = "div.main-content"
title = "h1"
author = ".author"
date = "time"
remove = [".sidebar"]

[[index]]
name = "Blog Archives"
url = "https://my-blog.com/archives"
type = "html"
items = "li.archive-item"
link = "a.item-link"

[[index]]
name = "Another Site"
url = "https://another-site.com/toc"
type = "html"
items = "div.chapter"
link = "a"

    # This [article] overrides the global one for this index only
    [article]
    content = "div.article-body-specific"
    title = "h2.chapter-title"
    author = "span.chapter-author"
    remove = ["#comments", ".ad-banner"]
    
    # Can also use Python for the override
    [article.python]
    script = """
    body = document.select_one("div.chapter-container")
    title_elem = document.select_one("h2.title")
    
    for nav in body.select("div.chapter-nav"):
        nav.decompose()
    
    return {
        "content": str(body),
        "title": title_elem.text.strip() if title_elem else None
    }
    """
```

---

## Processing Logic

### Overall Flow

1. Parse the `.gensi` TOML file
2. Extract global metadata (`title`, `author`, `language`)
3. Process `[cover]` section (if present)
4. For each `[[index]]` block (in order):
   - Fetch and parse the index source
   - Extract article list (using simple mode or `[index.python]`)
   - For each article without pre-provided `content`:
     - Fetch the article URL
     - Apply `[article]` rules (global or per-index override)
     - Extract content and metadata (title, author, date)
     - Use fallback metadata extraction if selectors don't match
5. Assemble EPUB with collected metadata, cover, and chapters
   - Group articles by their index `name` in the table of contents
   - Each index forms a section in the EPUB structure

### Python Script Execution

1. **Isolation**: Each script should be executed in a controlled environment
2. **Context Injection**: Inject the specified context variables before execution
3. **Return Value Validation**: Verify the returned value matches the expected type
4. **Error Handling**: Provide clear error messages if scripts fail or return invalid types

### URL Resolution

- All relative URLs encountered in CSS selector results or Python script returns must be converted to absolute URLs
- Base URL should be derived from the source page URL

### Content Ordering

- Articles appear in the EPUB in the order they are discovered
- Multiple `[[index]]` blocks are processed sequentially
- Within each index, articles maintain their list order

### EPUB Organization

- The EPUB table of contents should use the `name` field from each `[[index]]` to create sections
- Articles from each index are grouped under their respective index name
- This creates a hierarchical structure in the EPUB:
  - Index 1 Name
    - Article 1
    - Article 2
  - Index 2 Name
    - Article 3
    - Article 4

---

## Implementation Requirements

### Required Libraries/Features

1. **TOML Parser**: To parse `.gensi` files
2. **HTML Parser**: BeautifulSoup or lxml for `document` context
3. **Feed Parser**: feedparser or equivalent for RSS/Atom feeds
4. **Python Execution**: Safe execution environment for user scripts
5. **HTTP Client**: To fetch URLs
6. **EPUB Generator**: To create the final EPUB file
7. **Metadata Extraction**: Logic to extract metadata from HTML meta tags as fallback when CSS selectors don't match or aren't provided

### Python Execution Context

Each Python script type has specific context variables and expected return types:

| Section | Context Variable | Type | Return Type |
|---------|-----------------|------|-------------|
| `[cover.python]` | `document` | BeautifulSoup/lxml object | String (direct URL to cover image) |
| `[index.python]` (HTML) | `document` | BeautifulSoup/lxml object | List of dicts with `"url"` key (optional: `"content"`) |
| `[index.python]` (RSS) | `feed` | Feed object | List of dicts with `"url"` key (optional: `"content"`) |
| `[article.python]` | `document` | BeautifulSoup/lxml object | String (HTML content) OR Dict with `"content"` key (optional: `"title"`, `"author"`, `"date"`) |

### Error Handling

Implementations should handle:
- Invalid TOML syntax
- Missing required fields
- Network failures when fetching URLs
- CSS selector match failures
- Python script execution errors
- Python script return type mismatches
- Invalid URL formats

### Security Considerations

- **Sandbox Python Execution**: User scripts should run in a restricted environment
- **Validate URLs**: Check for malicious URLs before fetching
- **Limit Script Execution Time**: Prevent infinite loops
- **Restrict Imports**: Limit available Python modules in scripts

---

## Validation Rules

### Global Metadata
- `title` is required and must be a non-empty string
- `author` and `language` are optional strings
- `language` should match IETF BCP 47 format (warn if invalid)

### Cover Section
- If `[cover]` exists, `url` is required
- `selector` is only used if `url` doesn't point to an image file
- `[cover.python]` must return a string

### Index Section
- At least one `[[index]]` block is required
- Each `[[index]]` must have `name`, `url`, and `type`
- `name` must be a non-empty string
- `type` must be either `"html"` or `"rss"`
- For `type = "html"`: simple mode requires `items` and `link`
- For `type = "rss"`: `limit` must be a positive integer if provided
- `[index.python]` must return a list of dicts with required key `"url"`

### Article Section
- Simple mode requires `content` selector
- `title`, `author`, and `date` are optional selectors
- `remove` must be an array of strings if provided
- `[article.python]` must return either a string or a dictionary with `"content"` key
- If returning a dictionary, it may optionally include `"title"`, `"author"`, and `"date"` keys
- Per-index `[article]` overrides must be nested within `[[index]]` blocks

---

## Complete Examples

### Example 1: Simple HTML Blog

```toml
title = "My Favorite Blog"
author = "Blog Author"
language = "en"

[cover]
url = "https://my-blog.com/"
selector = "img.site-logo"

[[index]]
name = "Blog Archives"
url = "https://my-blog.com/archives"
type = "html"
items = "li.archive-item"
link = "a.item-link"

[article]
content = "div.post-body"
title = "h1.post-title"
author = "span.author-name"
date = "time.published"
remove = [
    ".sidebar",
    ".comment-form",
    "nav.post-navigation"
]
```

### Example 2: Complex RSS Feed

```toml
title = "Filtered News Feed"
author = "News, Inc."
language = "en"

[[index]]
name = "Technology News"
url = "https://example.com/news.rss"
type = "rss"

[index.python]
script = """
articles = []
for entry in feed.entries:
    tags = [tag.term for tag in entry.get("tags", [])]
    if "Technology" in tags and "Sponsor" not in tags:
        articles.append({
            "url": entry.link,
            "content": entry.content[0].value
        })
return articles[:15]
"""
```

### Example 3: Multiple Indices with Overrides

```toml
title = "Blog and News"
author = "Multi-Source"
language = "en"

[article]
content = "div.main-content"
title = "h1"
author = ".byline"
date = "time"
remove = [".sidebar", ".global-nav"]

[[index]]
name = "Blog Archives"
url = "https://my-blog.com/archives"
type = "html"
items = "li.archive-item"
link = "a.item-link"

[[index]]
name = "News Feed"
url = "https://example.com/news.rss"
type = "rss"
limit = 5

[[index]]
name = "Another Site Chapters"
url = "https://another-site.com/toc"
type = "html"
items = "div.chapter"
link = "a"

    [article]
    content = "div.article-body-specific"
    title = "h2.chapter-title"
    remove = ["#comments", ".ad-banner"]
    
    [article.python]
    script = """
    body = document.select_one("div.chapter-container")
    title_elem = document.select_one("h2.title")
    
    for nav in body.select("div.chapter-nav"):
        nav.decompose()
    
    return {
        "content": str(body),
        "title": title_elem.text.strip() if title_elem else None
    }
    """
```

---

## TOML Syntax Notes for Implementers

### Array of Tables: `[[index]]`

- Double brackets `[[index]]` denote an array of tables
- Each `[[index]]` block adds a new element to the array
- These are processed in order of appearance

### Nested Tables

- A table nested within an array element is denoted by the parent key followed by the child key
- Example: `[article]` nested in `[[index]]` is written as:

```toml
[[index]]
# index fields...

    [article]
    # article fields specific to this index...
```

### Inline Tables vs. Sections

- The format uses TOML sections (multi-line tables), not inline tables
- Arrays like `remove` use TOML array syntax: `["item1", "item2"]`

### Multi-line Strings

- Python scripts use TOML multi-line strings with triple quotes: `"""`
- Multi-line strings preserve formatting and newlines

---

## Appendix: CSS Selector Notes

### Expected Behavior

- Selectors should use standard CSS selector syntax
- Relative selectors (in `items` context) mean selecting within each matched item
- When extracting attributes like `href` or `src`, the implementation should:
  - Get the attribute value
  - Resolve relative URLs to absolute URLs
  - Handle missing attributes gracefully

### Common Patterns

- ID selectors: `#comments`
- Class selectors: `.post-title`, `.social-share-buttons`
- Element selectors: `article`, `h2`, `img`
- Attribute selectors: `img[data-src]`, `a[href]`
- Descendant combinators: `div.article-body p`
- Direct child combinators: `article > h2`

---

## Appendix: Feed Parser Notes

### Expected Feed Object Structure

When `type = "rss"`, the `feed` object should provide:

- `feed.entries`: List of entry objects
- Each entry should have:
  - `entry.title`: Entry title
  - `entry.link`: Entry URL
  - `entry.get("tags", [])`: List of tag objects (if available)
  - `entry.content`: Content array (if available)
    - `entry.content[0].value`: HTML content
  - Other standard RSS/Atom fields as applicable

### Recommended Library

- Python: `feedparser` library
- Supports both RSS and Atom feeds
- Normalizes feed formats to a consistent structure

---

## Version History

- **1.0** (Initial): Base specification with HTML and RSS index types, cover image support, and Python override system
