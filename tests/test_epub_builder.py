"""Tests for EPUB builder."""

import pytest
from pathlib import Path
from gensi.core.epub_builder import EPUBBuilder
from tests.helpers.epub_validator import EPUBValidator, validate_epub_structure


class TestEPUBBuilderBasic:
    """Test basic EPUB builder functionality."""

    def test_create_builder(self):
        """Test creating an EPUB builder."""
        builder = EPUBBuilder("Test Title", "Test Author", "en")

        assert builder.title == "Test Title"
        assert builder.author == "Test Author"
        assert builder.language == "en"

    def test_create_builder_minimal(self):
        """Test creating builder with minimal parameters."""
        builder = EPUBBuilder("Minimal Title")

        assert builder.title == "Minimal Title"
        assert builder.author == "Unknown"  # Default
        assert builder.language == "en"  # Default

    def test_add_cover(self, images_fixtures_dir):
        """Test adding cover image."""
        builder = EPUBBuilder("Test EPUB", "Author")
        cover_path = images_fixtures_dir / 'cover.jpg'
        cover_data = cover_path.read_bytes()

        builder.add_cover(cover_data)

        assert builder.cover_image is not None

    def test_add_section(self):
        """Test adding a section."""
        builder = EPUBBuilder("Test EPUB")

        builder.add_section("Section 1")
        builder.add_section("Section 2")

        assert len(builder.sections) == 2
        assert builder.sections[0]['name'] == "Section 1"
        assert builder.sections[1]['name'] == "Section 2"

    def test_add_section_unnamed(self):
        """Test adding unnamed section (for single index case)."""
        builder = EPUBBuilder("Test EPUB")

        builder.add_section(None)

        assert len(builder.sections) == 1
        assert builder.sections[0]['name'] is None

    def test_add_article(self):
        """Test adding an article."""
        builder = EPUBBuilder("Test EPUB")
        builder.add_section("Section 1")

        chapter = builder.add_article(
            content="<p>Article content</p>",
            title="Article Title",
            author="Article Author",
            date="2025-01-15"
        )

        assert chapter is not None
        assert len(builder.sections[0]['articles']) == 1

    def test_add_article_no_section_fails(self):
        """Test that adding article without section fails."""
        builder = EPUBBuilder("Test EPUB")

        with pytest.raises(ValueError, match="add_section"):
            builder.add_article(content="<p>Content</p>")

    def test_add_multiple_articles(self):
        """Test adding multiple articles to a section."""
        builder = EPUBBuilder("Test EPUB")
        builder.add_section("Section 1")

        for i in range(3):
            builder.add_article(
                content=f"<p>Article {i+1} content</p>",
                title=f"Article {i+1}"
            )

        assert len(builder.sections[0]['articles']) == 3


class TestEPUBBuilderBuild:
    """Test building EPUB files."""

    def test_build_simple_epub(self, temp_dir):
        """Test building a simple EPUB."""
        builder = EPUBBuilder("Test EPUB", "Test Author", "en")
        builder.add_section("Chapter 1")
        builder.add_article(
            content="<p>This is chapter 1 content.</p>",
            title="Chapter 1"
        )

        output_path = temp_dir / 'test.epub'
        builder.build(output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_build_epub_with_cover(self, temp_dir, images_fixtures_dir):
        """Test building EPUB with cover image."""
        builder = EPUBBuilder("Test EPUB with Cover", "Author")

        cover_path = images_fixtures_dir / 'cover.jpg'
        cover_data = cover_path.read_bytes()
        builder.add_cover(cover_data)

        builder.add_section("Content")
        builder.add_article(content="<p>Content</p>", title="Title")

        output_path = temp_dir / 'with_cover.epub'
        builder.build(output_path)

        assert output_path.exists()

        # Validate cover exists
        with EPUBValidator(output_path) as validator:
            assert validator.has_cover_image()

    def test_build_epub_multiple_sections(self, temp_dir):
        """Test building EPUB with multiple sections."""
        builder = EPUBBuilder("Multi-Section EPUB", "Author")

        # Section 1
        builder.add_section("Part 1")
        builder.add_article(content="<p>Chapter 1</p>", title="Chapter 1")
        builder.add_article(content="<p>Chapter 2</p>", title="Chapter 2")

        # Section 2
        builder.add_section("Part 2")
        builder.add_article(content="<p>Chapter 3</p>", title="Chapter 3")

        output_path = temp_dir / 'multi_section.epub'
        builder.build(output_path)

        assert output_path.exists()

        # Validate structure
        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) == 3  # 3 chapters

    def test_build_epub_metadata(self, temp_dir):
        """Test that EPUB metadata is correctly set."""
        builder = EPUBBuilder("Test Title", "Test Author", "es")
        builder.add_section("Content")
        builder.add_article(content="<p>Content</p>")

        output_path = temp_dir / 'metadata.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            metadata = validator.get_metadata()
            assert metadata['title'] == "Test Title"
            assert metadata['author'] == "Test Author"
            assert metadata['language'] == "es"

    def test_validate_epub_structure(self, temp_dir):
        """Test that generated EPUB has valid structure."""
        builder = EPUBBuilder("Valid EPUB", "Author")
        builder.add_section("Content")
        builder.add_article(content="<p>Test content</p>", title="Test")

        output_path = temp_dir / 'valid.epub'
        builder.build(output_path)

        results = validate_epub_structure(output_path)

        assert results['valid'] is True
        assert results['has_mimetype'] is True
        assert results['has_container'] is True
        assert results['has_content_opf'] is True
        assert results['spine_count'] > 0

    def test_build_epub_with_article_metadata(self, temp_dir):
        """Test building EPUB with article metadata."""
        builder = EPUBBuilder("Test EPUB", "Author")
        builder.add_section("Articles")

        builder.add_article(
            content="<p>Article content</p>",
            title="Article Title",
            author="Article Author",
            date="2025-01-15"
        )

        output_path = temp_dir / 'with_metadata.epub'
        builder.build(output_path)

        assert output_path.exists()

        # Check that article was created
        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            assert len(manifest) > 0

    def test_build_epub_single_index_no_sections(self, temp_dir):
        """Test building EPUB with single unnamed section (flat structure)."""
        builder = EPUBBuilder("Flat EPUB", "Author")
        builder.add_section(None)  # Unnamed section

        builder.add_article(content="<p>Article 1</p>", title="Article 1")
        builder.add_article(content="<p>Article 2</p>", title="Article 2")

        output_path = temp_dir / 'flat.epub'
        builder.build(output_path)

        assert output_path.exists()

        with EPUBValidator(output_path) as validator:
            spine_items = validator.get_spine_items()
            assert len(spine_items) == 2

    def test_epub_chapter_content(self, temp_dir):
        """Test that chapter content is correctly included."""
        builder = EPUBBuilder("Content Test", "Author")
        builder.add_section("Test")

        test_content = "<p>This is <strong>test</strong> content with <em>formatting</em>.</p>"
        builder.add_article(content=test_content, title="Test Chapter")

        output_path = temp_dir / 'content_test.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            # Get first chapter
            if spine_items:
                first_id = spine_items[0]
                first_href = manifest.get(first_id)
                if first_href:
                    chapter_content = validator.get_chapter_content(first_href)
                    assert chapter_content is not None
                    assert "test" in chapter_content
                    assert "formatting" in chapter_content


class TestEPUBBuilderStylesheets:
    """Test that stylesheet links are correctly included in EPUB files."""

    def test_article_has_stylesheet_link(self, temp_dir):
        """Test that article HTML contains stylesheet link."""
        builder = EPUBBuilder("Stylesheet Test", "Author")
        builder.add_section("Test")
        builder.add_article(content="<p>Test content</p>", title="Test Article")

        output_path = temp_dir / 'stylesheet_test.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            # Get first article
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

    def test_nav_has_stylesheet_link(self, temp_dir):
        """Test that nav document contains stylesheet link."""
        builder = EPUBBuilder("Nav Stylesheet Test", "Author")
        builder.add_section("Test")
        builder.add_article(content="<p>Test content</p>", title="Test Article")

        output_path = temp_dir / 'nav_stylesheet_test.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            # Find nav document
            opf_path = validator.get_content_opf_path()
            assert opf_path is not None

            import zipfile
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

    def test_multiple_articles_all_have_stylesheet_links(self, temp_dir):
        """Test that all article HTML files contain stylesheet links."""
        builder = EPUBBuilder("Multiple Articles Stylesheet Test", "Author")
        builder.add_section("Test")

        # Add multiple articles
        for i in range(5):
            builder.add_article(
                content=f"<p>Article {i+1} content</p>",
                title=f"Article {i+1}"
            )

        output_path = temp_dir / 'multi_articles_stylesheet.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            assert len(spine_items) == 5

            # Check each article for stylesheet link
            for item_id in spine_items:
                href = manifest.get(item_id)
                assert href is not None

                chapter_content = validator.get_chapter_content(href)
                assert chapter_content is not None

                # Verify stylesheet link exists
                assert '<link href="../styles/styles.css"' in chapter_content
                assert 'rel="stylesheet"' in chapter_content
                assert 'type="text/css"' in chapter_content

    def test_multiple_sections_all_articles_have_stylesheet_links(self, temp_dir):
        """Test that articles in multiple sections all have stylesheet links."""
        builder = EPUBBuilder("Multi-Section Stylesheet Test", "Author")

        # Section 1
        builder.add_section("Section 1")
        builder.add_article(content="<p>Section 1 Article 1</p>", title="S1A1")
        builder.add_article(content="<p>Section 1 Article 2</p>", title="S1A2")

        # Section 2
        builder.add_section("Section 2")
        builder.add_article(content="<p>Section 2 Article 1</p>", title="S2A1")
        builder.add_article(content="<p>Section 2 Article 2</p>", title="S2A2")

        output_path = temp_dir / 'multi_section_stylesheet.epub'
        builder.build(output_path)

        with EPUBValidator(output_path) as validator:
            manifest = validator.get_manifest_items()
            spine_items = validator.get_spine_items()

            assert len(spine_items) == 4

            # Check all articles have stylesheet links
            for item_id in spine_items:
                href = manifest.get(item_id)
                chapter_content = validator.get_chapter_content(href)

                assert '<link href="../styles/styles.css"' in chapter_content
                assert 'rel="stylesheet"' in chapter_content
                assert 'type="text/css"' in chapter_content
