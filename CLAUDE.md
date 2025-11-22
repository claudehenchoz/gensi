# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gensi is a Python application that generates EPUB files from web sources using `.gensi` recipe files (TOML-based). It features both a CLI (Click/Rich) and GUI (PySide6) interface with a Transmission-like queue design.

**Key capability:** Scrapes web content and RSS/Atom feeds, processes articles with CSS selectors or Python scripts, and assembles them into valid EPUB 2.0.1 files.

## Development Commands

### Package Management
This project uses **uv** (not pip) for dependency management:

```bash
# Install all dependencies
uv sync

# Install with dev dependencies (pytest, black, ruff)
uv sync --dev
```

### Running the Application

```bash
# GUI application
uv run gensi-gui

# CLI - process .gensi files
uv run gensi process <file.gensi>
uv run gensi process *.gensi --output-dir ./output --parallel 10 --verbose

# Cache management
uv run gensi process <file.gensi> --no-cache  # Disable caching for this run
uv run gensi clear-cache                       # Clear all cached data
```

### Testing and Code Quality

```bash
# Run tests
uv run pytest

# Format code (line length: 100)
uv run black src/

# Lint code
uv run ruff check src/
```

## Architecture

### Core Processing Pipeline

The architecture follows a clean pipeline pattern:

1. **Parser** (`core/parser.py`) - Parses and validates `.gensi` TOML files
2. **Cache** (`core/cache.py`) - Disk-based HTTP cache with 7-day TTL
3. **Fetcher** (`core/fetcher.py` + `core/cached_fetcher.py`) - HTTP client using curl_cffi with chrome136 impersonation, wrapped with intelligent caching
4. **Extractor** (`core/extractor.py`) - Extracts content using lxml CSS selectors or Python scripts
5. **Sanitizer** (`core/sanitizer.py`) - Sanitizes HTML with nh3 for EPUB compliance
6. **Typography** (`core/typography.py`) - Improves typography using typogrify
7. **Image Processor** (`core/image_processor.py`) - Downloads and embeds images
8. **EPUB Builder** (`core/epub_builder.py`) - Assembles EPUB using ebooklib and Jinja2 templates
9. **Processor** (`core/processor.py`) - Main orchestrator that coordinates the pipeline

### Key Design Patterns

**Python Override System**: Nearly every extraction step supports two modes:
- **Simple mode**: CSS selectors as strings (e.g., `content = "div.article-body"`)
- **Complex mode**: Python scripts with context injection (e.g., `[article.python]` with `document` variable)

Python scripts run in `core/python_executor.py` with restricted context (only `document` for HTML, `feed` for RSS).

**Parallel Processing**: The processor uses `asyncio.Semaphore` to limit concurrent article downloads (default: 5 parallel). Progress is reported via callbacks to the UI layer.

**Section/Article Hierarchy**:
- Multiple `[[index]]` blocks in `.gensi` files create sections
- Each index can override the global `[article]` extraction config
- Single index = flat structure; multiple indices = sectioned EPUB

**HTTP Caching**: Intelligent disk-based caching reduces network requests during development and recipe creation:
- **Cached**: Article HTML, images, cover images (7-day TTL)
- **Not cached**: Index pages and RSS/Atom feeds (always fetched fresh)
- **Storage**: System cache directory (e.g., `~/.cache/gensi/http_cache` on Linux, `%LOCALAPPDATA%\gensi\cache` on Windows)
- **Control**: `--no-cache` flag to disable caching, `gensi clear-cache` command to clear all cached data
- **Implementation**: `CachedFetcher` wraps `Fetcher` with context-aware caching logic in `core/cached_fetcher.py`

### File Organization

```
src/gensi/
├── cli.py              # Click commands with Rich progress bars
├── gui.py              # PySide6 GUI with queue-based interface
├── core/               # Core business logic (no UI dependencies)
│   ├── parser.py       # TOML parsing and validation
│   ├── cache.py        # HTTP response caching with TTL
│   ├── fetcher.py      # HTTP client wrapper
│   ├── cached_fetcher.py # Cached HTTP client with context-aware caching
│   ├── extractor.py    # Content extraction logic
│   ├── sanitizer.py    # HTML sanitization
│   ├── typography.py   # Typography improvements
│   ├── image_processor.py  # Image download and embedding
│   ├── python_executor.py  # Sandboxed Python script execution
│   ├── epub_builder.py # EPUB assembly
│   └── processor.py    # Main pipeline orchestrator
├── templates/          # Jinja2 templates for EPUB HTML
│   ├── article.xhtml.j2
│   ├── nav.xhtml.j2
│   └── styles.css
└── utils/              # Utility modules
    ├── url_utils.py
    └── metadata_fallback.py
```

### Important Implementation Details

**URL Resolution**: All relative URLs must be resolved to absolute URLs using `utils/url_utils.resolve_url()`. The base URL comes from the final URL after redirects (handled by fetcher).

**Metadata Fallback**: When CSS selectors fail to extract title/author/date, the extractor falls back to HTML meta tags (og:title, twitter:title, article:author, etc.) via `utils/metadata_fallback.py`.

**HTML Sanitization**: Content goes through `nh3` sanitizer which strips dangerous tags/attributes but keeps safe HTML. Empty content after sanitization triggers fallback wrapping logic in `processor.py:246-254`.

**Image Processing**: Images are downloaded, embedded as base64 or separate files in EPUB, and `<img>` tags are updated with new references. Configurable per-index via `images = true/false` in `[article]` section (default: true).

**Typography**: Uses typogrify to convert quotes, dashes, ellipses to proper typographic equivalents after sanitization.

**EPUB Structure**: Built using ebooklib. Sections map to EPUB spine structure. The nav document is auto-generated from sections and articles.

### Critical Validation Rules

From `.gensi` format spec (see `gensi-format-specification.md`):

1. `title` is required at top level
2. At least one `[[index]]` section is required
3. For HTML indices: must have `links` selector OR `[index.python]` script
4. For RSS indices: `limit` is optional, `use_content_encoded` controls whether to skip article fetching
5. `[article]` section requires `content` selector in simple mode OR `[article.python]` script
6. Multiple indices require `name` field for each (used for EPUB sections)
7. Python scripts must return specific types:
   - Cover: string (image URL)
   - Index: list of dicts with `"url"` key
   - Article: string (HTML) OR dict with `"content"` key

### Async/Threading Model

- **CLI**: Uses `asyncio.run()` to run async processor pipeline
- **GUI**: Runs processor in `QThread`, creates new event loop in thread (`ProcessorThread.run()`)
- **Core**: All fetching is async (`aiohttp` style with curl_cffi), parallel downloads managed with `asyncio.Semaphore`

Progress callbacks are synchronous and called from async context, so GUI thread safety is handled by Qt signals.

## Common Development Tasks

### Adding a New Extraction Feature

1. Modify the `.gensi` format spec if adding new TOML fields
2. Update validation in `core/parser.py:_validate()`
3. Implement extraction logic in `core/extractor.py`
4. Update `core/processor.py` to wire the new feature into the pipeline
5. Add corresponding CLI options in `cli.py` if needed

### Modifying HTML Sanitization Rules

Edit `core/sanitizer.py`. Uses nh3 library with configurable allowed tags/attributes.

### Changing EPUB Output Format

1. Modify Jinja2 templates in `templates/`
2. Update `core/epub_builder.py` if changing structure/metadata
3. Ensure compliance with EPUB 2.0.1 spec

### Debugging Python Script Execution

Python scripts execute in restricted context via `exec()` in `core/python_executor.py`. Only injected variables are available. To debug issues:
1. Check what's in the context (e.g., `document`, `feed`)
2. Verify return type matches spec requirements
3. Look for exceptions in error messages (they bubble up from executor)

## Output File Naming

Output EPUB files are named using slugified title: `slugify(self.parser.title) + ".epub"` (see `processor.py:313`). This was recently added (commit 77b98e0).

## Recent Changes

Based on git log:
- Typographical improvements added (commit 24ae6c0)
- Output filename now slugified (commit 77b98e0)
- Fixed 'nav' errors with epubcheck validation (commit f9a20d5)
- Made images configurable in article section (commit f9a20d5)
- Added image retrieval and storage (commit 04436fa)

## Testing

### Run All Tests
```bash
uv run pytest
```

### Run with Verbose Output
```bash
uv run pytest -v
```

### Run Specific Test File
```bash
uv run pytest tests/test_parser.py -v
```

### Run Specific Test
```bash
uv run pytest tests/test_parser.py::TestParserValidFiles::test_parse_simple_gensi -v
```

### Run Only Passing Tests
```bash
uv run pytest --lf --last-failed-no-failures none
```

### Save Generated EPUBs from Tests
Tests can optionally save all generated EPUB files to a specified directory for external validation (e.g., with epubcheck):

```bash
# Save all EPUB files generated during tests
uv run pytest --epub-output=./test_epubs

# Run specific tests and save EPUBs
uv run pytest tests/test_integration.py --epub-output=./output/epubs -v

# Useful for validation with epubcheck
uv run pytest --epub-output=./test_epubs
epubcheck test_epubs/*.epub
```

Each EPUB will be saved with a name matching the test that generated it (e.g., `test_process_simple_gensi.epub`, `test_build_epub_with_cover.epub`).
