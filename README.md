# Gensi - EPUB Generator from Web Sources

Gensi is a powerful Python application that generates EPUB files from web sources using `.gensi` recipe files. It supports both a graphical user interface (GUI) and a command-line interface (CLI).

## Features

- **Dual Interface**: Both GUI (PySide6) and CLI (Click) applications
- **Web Scraping**: Uses curl_cffi with chrome136 impersonation for reliable web content retrieval
- **Flexible Extraction**: CSS selectors or Python scripts for content extraction
- **RSS/Atom Support**: Import articles from RSS/Atom feeds
- **Parallel Processing**: Downloads up to 5 articles in parallel
- **EPUB 2.0.1 Compliant**: Generates valid EPUB files with proper sanitization
- **Transmission-like GUI**: Queue-based interface similar to the popular BitTorrent client
- **Customizable Templates**: Jinja2 templates for consistent article styling

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Install uv

If you don't have `uv` installed:

```bash
# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Gensi

1. Clone or download this repository
2. Navigate to the project directory
3. Install dependencies using uv:

```bash
# Install the project and all dependencies
uv sync

# Or install in development mode
uv sync --dev
```

## Usage

### GUI Application

Launch the GUI application:

```bash
# Using uv
uv run gensi-gui

# Or after installation
gensi-gui
```

**GUI Features:**
- Add multiple .gensi files to the processing queue
- Monitor download progress with progress bars
- View cover images as they're downloaded
- Keep completed items in the list for reference
- Configure output directory in settings

### CLI Application

Process .gensi files from the command line:

```bash
# Process a single file
uv run gensi process book.gensi

# Process multiple files
uv run gensi process book1.gensi book2.gensi

# Process with custom output directory
uv run gensi process *.gensi --output-dir ./output

# Adjust parallel downloads
uv run gensi process book.gensi --parallel 10

# Verbose output
uv run gensi process book.gensi --verbose
```

**CLI Options:**
- `-o, --output-dir PATH`: Output directory for EPUB files (default: same as input file)
- `-p, --parallel N`: Maximum number of parallel downloads (default: 5)
- `-v, --verbose`: Verbose output

## .gensi File Format

The `.gensi` format is a TOML-based recipe format for generating EPUB files from web sources. See [gensi-format-specification.md](gensi-format-specification.md) for the complete specification.

### Basic Example

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

### Advanced Example with Python

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

## Project Structure

```
gensi/
├── pyproject.toml          # Project configuration (managed by uv)
├── README.md               # This file
├── gensi-format-specification.md  # Format specification
├── src/gensi/
│   ├── __init__.py
│   ├── cli.py              # Click CLI interface
│   ├── gui.py              # PySide6 GUI interface
│   ├── core/               # Core processing modules
│   │   ├── parser.py       # .gensi TOML parser
│   │   ├── fetcher.py      # curl_cffi web fetcher
│   │   ├── extractor.py    # Content extraction with lxml
│   │   ├── sanitizer.py    # HTML sanitization with nh3
│   │   ├── python_executor.py  # User script execution
│   │   ├── epub_builder.py # EPUB generation
│   │   └── processor.py    # Main orchestration
│   ├── templates/          # Jinja2 templates
│   │   ├── article.xhtml.j2
│   │   ├── nav.xhtml.j2
│   │   └── styles.css
│   └── utils/              # Utility modules
│       ├── url_utils.py
│       └── metadata_fallback.py
└── tests/                  # Test files
```

## Technology Stack

- **PySide6**: GUI framework
- **Click**: CLI framework
- **Rich**: CLI progress bars and formatting
- **curl_cffi**: HTTP client with browser impersonation
- **lxml**: HTML parsing and CSS selectors
- **nh3**: HTML sanitization for EPUB compliance
- **feedparser**: RSS/Atom feed parsing
- **Jinja2**: Template engine for article layout
- **ebooklib**: EPUB file generation
- **asyncio**: Async parallel processing

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
# Format code with black
uv run black src/

# Lint with ruff
uv run ruff check src/
```

### Installing Development Dependencies

```bash
uv sync --dev
```

## Registering .gensi File Association (Windows)

To make the GUI the default handler for `.gensi` files on Windows:

1. Right-click a `.gensi` file
2. Select "Open with" → "Choose another app"
3. Click "More apps" → "Look for another app on this PC"
4. Navigate to where `gensi-gui.exe` is installed (usually in your Python Scripts directory)
5. Check "Always use this app to open .gensi files"

Alternatively, run this PowerShell script as administrator:

```powershell
$gensiPath = (Get-Command gensi-gui).Path
$progId = "Gensi.File"

# Register file association
New-Item -Path "HKCR:\.gensi" -Force
Set-ItemProperty -Path "HKCR:\.gensi" -Name "(Default)" -Value $progId

# Register program
New-Item -Path "HKCR:\$progId" -Force
Set-ItemProperty -Path "HKCR:\$progId" -Name "(Default)" -Value "Gensi Recipe File"

New-Item -Path "HKCR:\$progId\shell\open\command" -Force
Set-ItemProperty -Path "HKCR:\$progId\shell\open\command" -Name "(Default)" -Value "`"$gensiPath`" `"%1`""
```

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please visit the [GitHub Issues](https://github.com/yourusername/gensi/issues) page.
