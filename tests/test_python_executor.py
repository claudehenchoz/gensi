"""Tests for Python script executor."""

import pytest
from lxml import html
from gensi.core.python_executor import PythonExecutor


class TestPythonExecutor:
    """Test Python script execution."""

    @pytest.fixture
    def executor(self):
        """Create a Python executor instance."""
        return PythonExecutor()

    def test_execute_simple_return(self, executor):
        """Test executing script with simple return."""
        script = "return 'hello'"
        result = executor.execute(script, {})

        assert result == 'hello'

    def test_execute_with_context(self, executor):
        """Test executing script with context variables."""
        script = "return value * 2"
        context = {'value': 21}
        result = executor.execute(script, context)

        assert result == 42

    def test_execute_list_comprehension(self, executor):
        """Test executing script with list comprehension."""
        script = "return [x * 2 for x in numbers]"
        context = {'numbers': [1, 2, 3, 4, 5]}
        result = executor.execute(script, context)

        assert result == [2, 4, 6, 8, 10]

    def test_execute_with_document_context(self, executor):
        """Test executing script with document context."""
        html_content = """
<html>
<body>
    <div class="item">Item 1</div>
    <div class="item">Item 2</div>
    <div class="item">Item 3</div>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        script = """
items = document.cssselect('.item')
return len(items)
"""
        context = {'document': doc}
        result = executor.execute(script, context)

        assert result == 3

    def test_execute_extracting_urls(self, executor):
        """Test executing script that extracts URLs."""
        html_content = """
<html>
<body>
    <a href="/page1.html">Page 1</a>
    <a href="/page2.html">Page 2</a>
    <a href="/page3.html">Page 3</a>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        script = """
links = []
for elem in document.cssselect('a'):
    links.append({'url': elem.get('href')})
return links
"""
        context = {'document': doc}
        result = executor.execute(script, context)

        assert len(result) == 3
        assert result[0]['url'] == '/page1.html'
        assert result[1]['url'] == '/page2.html'

    def test_execute_conditional_logic(self, executor):
        """Test executing script with conditional logic."""
        html_content = """
<html>
<body>
    <div class="post" data-featured="true">Featured</div>
    <div class="post">Regular</div>
    <div class="post" data-featured="true">Also Featured</div>
</body>
</html>
"""
        doc = html.fromstring(html_content)
        script = """
featured = []
for elem in document.cssselect('.post'):
    if elem.get('data-featured') == 'true':
        featured.append(elem.text)
return featured
"""
        context = {'document': doc}
        result = executor.execute(script, context)

        assert len(result) == 2
        assert 'Featured' in result
        assert 'Also Featured' in result
        assert 'Regular' not in result

    def test_execute_implicit_return(self, executor):
        """Test executing script with implicit return (last expression)."""
        script = "42"
        result = executor.execute(script, {})

        assert result == 42

    def test_execute_multiline_script(self, executor):
        """Test executing multi-line script."""
        script = """
a = 10
b = 20
c = a + b
return c * 2
"""
        result = executor.execute(script, {})

        assert result == 60

    def test_execute_syntax_error(self, executor):
        """Test that syntax errors are raised."""
        script = "return invalid syntax here"

        with pytest.raises(Exception):  # Should raise SyntaxError
            executor.execute(script, {})

    def test_execute_runtime_error(self, executor):
        """Test that runtime errors are raised."""
        script = "return undefined_variable"

        with pytest.raises(Exception):  # Should raise NameError
            executor.execute(script, {})

    def test_execute_no_return(self, executor):
        """Test executing script without return statement."""
        script = "x = 42"
        result = executor.execute(script, {})

        # Should return None if no explicit return
        assert result is None

    def test_execute_return_dict(self, executor):
        """Test executing script that returns dictionary."""
        script = """
return {
    'content': '<p>Test content</p>',
    'title': 'Test Title',
    'author': 'Test Author'
}
"""
        result = executor.execute(script, {})

        assert isinstance(result, dict)
        assert result['content'] == '<p>Test content</p>'
        assert result['title'] == 'Test Title'

    def test_execute_with_feed_context(self, executor):
        """Test executing script with feed context (RSS/Atom)."""
        # Simulate a feed object
        class FakeEntry:
            def __init__(self, link, title):
                self.link = link
                self.title = title

        class FakeFeed:
            def __init__(self):
                self.entries = [
                    FakeEntry('http://example.com/1', 'Entry 1'),
                    FakeEntry('http://example.com/2', 'Entry 2'),
                ]

        feed = FakeFeed()
        script = """
articles = []
for entry in feed.entries:
    articles.append({'url': entry.link, 'title': entry.title})
return articles
"""
        context = {'feed': feed}
        result = executor.execute(script, context)

        assert len(result) == 2
        assert result[0]['url'] == 'http://example.com/1'
        assert result[1]['title'] == 'Entry 2'

    def test_execute_string_manipulation(self, executor):
        """Test executing script with string manipulation."""
        script = """
text = document.text
return text.upper().strip()
"""
        class FakeDoc:
            text = "  hello world  "

        context = {'document': FakeDoc()}
        result = executor.execute(script, context)

        assert result == "HELLO WORLD"
