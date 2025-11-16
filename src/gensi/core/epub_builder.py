"""EPUB 2.0.1 builder using ebooklib and jinja2 templates."""

from pathlib import Path
from typing import Optional
from ebooklib import epub
from jinja2 import Environment, FileSystemLoader
import uuid


class EPUBBuilder:
    """Builds EPUB files from processed articles."""

    def __init__(self, title: str, author: Optional[str] = None, language: str = 'en'):
        """
        Initialize the EPUB builder.

        Args:
            title: The EPUB title
            author: The EPUB author
            language: The EPUB language code (default: 'en')
        """
        self.title = title
        self.author = author or 'Unknown'
        self.language = language

        # Create EPUB book
        self.book = epub.EpubBook()
        self.book.set_identifier(str(uuid.uuid4()))
        self.book.set_title(title)
        self.book.set_language(language)
        self.book.add_author(self.author)

        # Initialize jinja2
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

        # Storage for chapters and sections
        self.sections = []
        self.chapters = []
        self.cover_image = None

    def add_cover(self, image_data: bytes, image_name: str = 'cover.jpg'):
        """
        Add a cover image to the EPUB.

        Args:
            image_data: The image binary data
            image_name: The filename for the cover image
        """
        self.cover_image = image_name
        self.book.set_cover(image_name, image_data)

    def add_section(self, section_name: Optional[str] = None):
        """
        Start a new section in the EPUB.

        Args:
            section_name: The name of the section (None for root-level articles)
        """
        self.sections.append({
            'name': section_name,
            'articles': []
        })

    def add_article(
        self,
        content: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[str] = None,
        filename: Optional[str] = None,
        images: Optional[dict] = None
    ) -> epub.EpubHtml:
        """
        Add an article to the current section.

        Args:
            content: The HTML content of the article
            title: The article title
            author: The article author
            date: The publication date
            filename: The filename for this chapter (auto-generated if None)

        Returns:
            The created EpubHtml chapter
        """
        if not self.sections:
            raise ValueError("Must call add_section() before add_article()")

        # Generate filename if not provided
        if not filename:
            chapter_num = len(self.chapters) + 1
            filename = f'chapter_{chapter_num:03d}.xhtml'

        # Render article template
        template = self.jinja_env.get_template('article.xhtml.j2')
        article_html = template.render(
            title=title or 'Untitled',
            author=author,
            date=date,
            content=content,
            language=self.language
        )

        # Create chapter
        chapter = epub.EpubHtml(
            title=title or 'Untitled',
            file_name=f'text/{filename}',
            lang=self.language
        )
        # Use set_content() to properly encode the HTML
        chapter.set_content(article_html.encode('utf-8'))

        # Add to book
        self.book.add_item(chapter)
        self.chapters.append(chapter)

        # Add images if present
        if images:
            for img_url, (img_filename, img_data) in images.items():
                # Determine media type from filename
                ext = img_filename.split('.')[-1].lower()
                media_type_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp',
                    'svg': 'image/svg+xml',
                    'bmp': 'image/bmp'
                }
                media_type = media_type_map.get(ext, 'image/jpeg')

                # Create image item
                img_item = epub.EpubItem(
                    uid=f"img_{img_filename}",
                    file_name=f"images/{img_filename}",
                    media_type=media_type,
                    content=img_data
                )
                self.book.add_item(img_item)

        # Add to current section
        self.sections[-1]['articles'].append({
            'title': title or 'Untitled',
            'href': f'text/{filename}',
            'chapter': chapter
        })

        return chapter

    def build(self, output_path: Path | str):
        """
        Build and save the EPUB file.

        Args:
            output_path: Path where the EPUB file will be saved
        """
        output_path = Path(output_path)

        # Add CSS
        template_dir = Path(__file__).parent.parent / 'templates'
        css_path = template_dir / 'styles.css'
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="styles/styles.css",
            media_type="text/css",
            content=css_content.encode('utf-8')
        )
        self.book.add_item(nav_css)

        # Build table of contents
        toc = []
        spine = []

        for section in self.sections:
            for article in section['articles']:
                spine.append(article['chapter'])

            # If section has a name, create a nested structure
            # Otherwise, add articles directly to root (for single index)
            if section['name']:
                section_toc = [article['chapter'] for article in section['articles']]
                toc.append((
                    epub.Section(section['name']),
                    section_toc
                ))
            else:
                # Add articles directly to root TOC
                for article in section['articles']:
                    toc.append(article['chapter'])

        self.book.toc = toc
        self.book.spine = spine

        # Add navigation files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Write EPUB file
        # Use options to avoid issues with nav generation
        options = {'epub3_pages': False}
        epub.write_epub(str(output_path), self.book, options)


def create_epub(
    title: str,
    sections: list[dict],
    output_path: Path | str,
    author: Optional[str] = None,
    language: str = 'en',
    cover_data: Optional[bytes] = None,
    cover_name: str = 'cover.jpg'
) -> None:
    """
    Convenience function to create an EPUB file.

    Args:
        title: The EPUB title
        sections: List of sections, each containing articles
        output_path: Path where the EPUB file will be saved
        author: The EPUB author
        language: The EPUB language code
        cover_data: Cover image binary data
        cover_name: Cover image filename

    Example:
        sections = [
            {
                'name': 'Section 1',
                'articles': [
                    {
                        'title': 'Article 1',
                        'content': '<p>Content</p>',
                        'author': 'Author',
                        'date': '2024-01-01'
                    }
                ]
            }
        ]
    """
    builder = EPUBBuilder(title, author, language)

    if cover_data:
        builder.add_cover(cover_data, cover_name)

    for section in sections:
        builder.add_section(section['name'])
        for article in section['articles']:
            builder.add_article(
                content=article['content'],
                title=article.get('title'),
                author=article.get('author'),
                date=article.get('date')
            )

    builder.build(output_path)
