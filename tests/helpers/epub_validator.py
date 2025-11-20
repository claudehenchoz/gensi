"""Helper functions for validating EPUB file structure and content."""

import zipfile
from pathlib import Path
from typing import Optional
from lxml import etree


class EPUBValidator:
    """Validates EPUB file structure and content."""

    def __init__(self, epub_path: Path):
        """Initialize validator with EPUB file path."""
        self.epub_path = Path(epub_path)
        self.epub = zipfile.ZipFile(epub_path, 'r')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.epub.close()

    def validate_mimetype(self) -> bool:
        """Validate that mimetype file exists and has correct content."""
        try:
            mimetype = self.epub.read('mimetype').decode('utf-8')
            return mimetype == 'application/epub+zip'
        except KeyError:
            return False

    def validate_container_xml(self) -> bool:
        """Validate that META-INF/container.xml exists and is valid."""
        try:
            content = self.epub.read('META-INF/container.xml')
            tree = etree.fromstring(content)
            # Check for rootfile element
            rootfiles = tree.xpath(
                '//container:rootfile',
                namespaces={'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            )
            return len(rootfiles) > 0
        except (KeyError, etree.XMLSyntaxError):
            return False

    def get_content_opf_path(self) -> Optional[str]:
        """Get the path to content.opf from container.xml."""
        try:
            content = self.epub.read('META-INF/container.xml')
            tree = etree.fromstring(content)
            rootfiles = tree.xpath(
                '//container:rootfile/@full-path',
                namespaces={'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            )
            return rootfiles[0] if rootfiles else None
        except (KeyError, etree.XMLSyntaxError):
            return None

    def get_metadata(self) -> dict:
        """Extract metadata from content.opf."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return {}

        try:
            content = self.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf', 'dc': 'http://purl.org/dc/elements/1.1/'}

            metadata = {}
            title = tree.xpath('//dc:title/text()', namespaces=ns)
            if title:
                metadata['title'] = title[0]

            creator = tree.xpath('//dc:creator/text()', namespaces=ns)
            if creator:
                metadata['author'] = creator[0]

            language = tree.xpath('//dc:language/text()', namespaces=ns)
            if language:
                metadata['language'] = language[0]

            return metadata
        except (KeyError, etree.XMLSyntaxError):
            return {}

    def get_spine_items(self) -> list[str]:
        """Get list of spine item IDs in order."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return []

        try:
            content = self.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}

            idrefs = tree.xpath('//opf:spine/opf:itemref/@idref', namespaces=ns)
            return idrefs
        except (KeyError, etree.XMLSyntaxError):
            return []

    def get_manifest_items(self) -> dict:
        """Get manifest items as dict {id: href}."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return {}

        try:
            content = self.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}

            items = tree.xpath('//opf:manifest/opf:item', namespaces=ns)
            manifest = {}
            for item in items:
                item_id = item.get('id')
                href = item.get('href')
                if item_id and href:
                    manifest[item_id] = href
            return manifest
        except (KeyError, etree.XMLSyntaxError):
            return {}

    def get_chapter_content(self, href: str) -> Optional[str]:
        """Get content of a chapter by href (relative to content.opf)."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return None

        # Construct full path
        opf_dir = str(Path(opf_path).parent)
        if opf_dir == '.':
            full_path = href
        else:
            full_path = f"{opf_dir}/{href}"

        try:
            content = self.epub.read(full_path).decode('utf-8')
            return content
        except KeyError:
            return None

    def has_cover_image(self) -> bool:
        """Check if EPUB has a cover image."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return False

        try:
            content = self.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}

            # Check for cover item in manifest
            cover_items = tree.xpath(
                '//opf:manifest/opf:item[@properties="cover-image"]',
                namespaces=ns
            )
            if cover_items:
                return True

            # Check for cover metadata
            cover_meta = tree.xpath(
                '//opf:metadata/opf:meta[@name="cover"]',
                namespaces=ns
            )
            return len(cover_meta) > 0

        except (KeyError, etree.XMLSyntaxError):
            return False

    def get_nav_toc(self) -> list:
        """Get table of contents structure from nav file."""
        opf_path = self.get_content_opf_path()
        if not opf_path:
            return []

        try:
            content = self.epub.read(opf_path)
            tree = etree.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}

            # Find nav document
            nav_items = tree.xpath(
                '//opf:manifest/opf:item[@properties="nav"]/@href',
                namespaces=ns
            )
            if not nav_items:
                return []

            nav_href = nav_items[0]
            opf_dir = str(Path(opf_path).parent)
            if opf_dir == '.':
                nav_path = nav_href
            else:
                nav_path = f"{opf_dir}/{nav_href}"

            nav_content = self.epub.read(nav_path)
            nav_tree = etree.fromstring(nav_content)

            # Extract TOC items
            # This is a simplified extraction - full implementation would handle nested lists
            xhtml_ns = {'xhtml': 'http://www.w3.org/1999/xhtml'}
            nav_items = nav_tree.xpath('//xhtml:nav[@*="toc"]//xhtml:a', namespaces=xhtml_ns)

            toc = []
            for item in nav_items:
                title = ''.join(item.itertext()).strip()
                href = item.get('href', '')
                toc.append({'title': title, 'href': href})

            return toc

        except (KeyError, etree.XMLSyntaxError):
            return []

    def list_files(self) -> list[str]:
        """List all files in the EPUB."""
        return self.epub.namelist()

    def count_images(self) -> int:
        """Count number of image files in EPUB."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        count = 0
        for filename in self.epub.namelist():
            if Path(filename).suffix.lower() in image_extensions:
                count += 1
        return count

    def get_articles(self) -> list[str]:
        """Get list of all article contents from the EPUB spine."""
        spine_items = self.get_spine_items()
        manifest = self.get_manifest_items()

        articles = []
        for item_id in spine_items:
            href = manifest.get(item_id)
            if href:
                content = self.get_chapter_content(href)
                if content:
                    articles.append(content)

        return articles


def validate_epub_structure(epub_path: Path) -> dict:
    """
    Validate basic EPUB structure and return results.

    Returns dict with validation results:
    {
        'valid': bool,
        'has_mimetype': bool,
        'has_container': bool,
        'has_content_opf': bool,
        'metadata': dict,
        'spine_count': int,
        'has_cover': bool
    }
    """
    results = {
        'valid': False,
        'has_mimetype': False,
        'has_container': False,
        'has_content_opf': False,
        'metadata': {},
        'spine_count': 0,
        'has_cover': False
    }

    try:
        with EPUBValidator(epub_path) as validator:
            results['has_mimetype'] = validator.validate_mimetype()
            results['has_container'] = validator.validate_container_xml()
            results['has_content_opf'] = validator.get_content_opf_path() is not None
            results['metadata'] = validator.get_metadata()
            results['spine_count'] = len(validator.get_spine_items())
            results['has_cover'] = validator.has_cover_image()

            results['valid'] = (
                results['has_mimetype'] and
                results['has_container'] and
                results['has_content_opf'] and
                results['spine_count'] > 0
            )

    except Exception:
        pass

    return results
