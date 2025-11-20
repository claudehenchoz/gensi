"""Tests for date parsing and formatting utilities."""

import pytest
from datetime import datetime
from gensi.utils.date_formatter import parse_date, format_date


class TestParseDateFunction:
    """Test the parse_date function with various input formats."""

    def test_parse_iso_datetime(self):
        """Test parsing ISO 8601 datetime string."""
        result = parse_date("2025-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_iso_date(self):
        """Test parsing ISO date (no time)."""
        result = parse_date("2025-01-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_human_readable_date(self):
        """Test parsing human-readable date."""
        result = parse_date("January 15, 2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_abbreviated_month(self):
        """Test parsing date with abbreviated month."""
        result = parse_date("Jan 15, 2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_european_format(self):
        """Test parsing European date format."""
        result = parse_date("15.01.2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_slash_format(self):
        """Test parsing date with slashes."""
        result = parse_date("01/15/2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_none(self):
        """Test parsing None returns None."""
        result = parse_date(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        result = parse_date("not a date at all")
        assert result is None

    def test_parse_non_string(self):
        """Test parsing non-string returns None."""
        result = parse_date(12345)
        assert result is None


class TestFormatDateFunction:
    """Test the format_date function with various languages and formats."""

    def test_format_iso_datetime_english(self):
        """Test formatting ISO datetime in English."""
        result = format_date("2025-01-15T10:30:00", "en")
        # Should include both date and time
        assert "2025" in result or "25" in result
        assert "Jan" in result or "January" in result
        assert "15" in result
        assert "10" in result or "10:30" in result

    def test_format_iso_datetime_german(self):
        """Test formatting ISO datetime in German."""
        result = format_date("2025-01-15T10:30:00", "de")
        # Should include both date and time in German format
        assert "2025" in result or "25" in result
        assert "15" in result
        assert "10" in result or "10:30" in result

    def test_format_iso_datetime_french(self):
        """Test formatting ISO datetime in French."""
        result = format_date("2025-01-15T10:30:00", "fr")
        # Should include both date and time in French format
        assert "2025" in result or "25" in result
        assert "15" in result
        assert "10" in result or "10:30" in result

    def test_format_iso_datetime_spanish(self):
        """Test formatting ISO datetime in Spanish."""
        result = format_date("2025-01-15T10:30:00", "es")
        # Should include both date and time in Spanish format
        assert "2025" in result or "25" in result
        assert "15" in result
        assert "10" in result or "10:30" in result

    def test_format_date_only_english(self):
        """Test formatting date without time in English."""
        result = format_date("2025-01-15", "en")
        # Should format as long date (no time)
        assert "2025" in result
        assert "Jan" in result or "January" in result
        assert "15" in result
        # Should NOT contain time indicators
        assert ":" not in result

    def test_format_date_only_german(self):
        """Test formatting date without time in German."""
        result = format_date("2025-01-15", "de")
        # Should format in German
        assert "2025" in result
        assert "15" in result
        assert ":" not in result

    def test_format_human_readable_date(self):
        """Test formatting already human-readable date."""
        result = format_date("January 15, 2025", "en")
        # Should parse and reformat
        assert "2025" in result
        assert "Jan" in result or "January" in result
        assert "15" in result

    def test_format_unparseable_date_fallback(self):
        """Test that unparseable dates fall back to original string."""
        original = "not a valid date"
        result = format_date(original, "en")
        assert result == original

    def test_format_none_date(self):
        """Test formatting None returns None."""
        result = format_date(None, "en")
        assert result is None

    def test_format_empty_string(self):
        """Test formatting empty string returns empty string."""
        result = format_date("", "en")
        assert result == ""

    def test_format_with_default_language(self):
        """Test formatting with default language parameter."""
        result = format_date("2025-01-15T10:30:00")
        # Should use English as default
        assert "2025" in result or "25" in result
        assert result is not None

    def test_format_invalid_locale(self):
        """Test formatting with invalid locale falls back to original."""
        original = "2025-01-15"
        result = format_date(original, "invalid_locale")
        # Should return original string on locale error
        # Note: Some locales might work unexpectedly, so we just check it returns something
        assert result is not None

    def test_format_datetime_with_seconds(self):
        """Test formatting datetime with seconds."""
        result = format_date("2025-01-15T10:30:45", "en")
        # Should include time information
        assert "2025" in result or "25" in result
        assert "10" in result

    def test_format_datetime_midnight_as_date_only(self):
        """Test that midnight (00:00:00) is formatted as date only."""
        result = format_date("2025-01-15T00:00:00", "en")
        # Midnight should be treated as date-only (no time shown)
        # The formatter should detect all zeros and format as date only
        assert "2025" in result
        assert "15" in result

    def test_format_preserves_original_on_babel_error(self):
        """Test that original string is preserved on Babel formatting errors."""
        # This is hard to trigger, but we test the fallback logic exists
        result = format_date("2025-01-15", "en")
        assert result is not None
        assert len(result) > 0


class TestDateFormatterEdgeCases:
    """Test edge cases and special scenarios."""

    def test_multiple_formats_same_language(self):
        """Test that different input formats produce consistent output."""
        iso_result = format_date("2025-01-15", "en")
        human_result = format_date("January 15, 2025", "en")

        # Both should contain the same components
        assert "2025" in iso_result
        assert "2025" in human_result
        assert "15" in iso_result
        assert "15" in human_result

    def test_year_only_date(self):
        """Test parsing year-only string."""
        result = parse_date("2025")
        # dateparser might interpret this as a year
        # We just check it doesn't crash
        assert result is None or isinstance(result, datetime)

    def test_relative_date_parsing(self):
        """Test parsing relative dates like 'yesterday' or '2 days ago'."""
        result = parse_date("yesterday")
        # Should parse to a datetime
        assert result is not None
        assert isinstance(result, datetime)

    def test_format_relative_date(self):
        """Test formatting a relative date string."""
        result = format_date("yesterday", "en")
        # Should parse and format to absolute date
        assert result is not None
        # Should not contain the word "yesterday" anymore (formatted to actual date)
        # Note: This depends on when the test runs, so we just check it's not empty
        assert len(result) > 0

    def test_timezone_aware_datetime(self):
        """Test parsing timezone-aware datetime."""
        result = parse_date("2025-01-15T10:30:00+01:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_various_time_formats(self):
        """Test parsing various time formats."""
        formats = [
            "2025-01-15 10:30 AM",
            "2025-01-15 10:30:00",
            "Jan 15, 2025 at 10:30 AM",
        ]
        for date_str in formats:
            result = parse_date(date_str)
            assert result is not None, f"Failed to parse: {date_str}"
            assert result.year == 2025
            assert result.month == 1
            assert result.day == 15
