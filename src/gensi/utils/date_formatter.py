"""Date parsing and formatting utilities for EPUB output."""

from datetime import datetime
from typing import Optional

import dateparser
from babel.dates import format_datetime, format_date as babel_format_date
from babel.core import UnknownLocaleError


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.

    Uses dateparser to handle various date formats including:
    - ISO 8601: "2025-01-15T10:00:00Z"
    - Human-readable: "January 15, 2025"
    - Relative dates: "2 hours ago"

    Args:
        date_string: The date string to parse

    Returns:
        A datetime object if parsing succeeds, None otherwise
    """
    if not date_string or not isinstance(date_string, str):
        return None

    try:
        # Use dateparser with sensible defaults
        parsed = dateparser.parse(
            date_string,
            settings={
                'RETURN_AS_TIMEZONE_AWARE': False,  # Keep as naive datetime
                'PREFER_DATES_FROM': 'past',  # Articles are usually from the past
            }
        )
        return parsed
    except (ValueError, TypeError, AttributeError):
        return None


def format_date(date_string: str, language: str = 'en') -> str:
    """
    Format a date string into a human-readable format based on language.

    Parses the date string and formats it according to the locale specified by
    the language parameter. Includes time information if present in the source.
    Falls back to the original string if parsing fails.

    Args:
        date_string: The date string to format
        language: The language/locale code (e.g., 'en', 'de', 'fr')

    Returns:
        A formatted date string in the locale's default format, or the original
        string if parsing fails

    Examples:
        >>> format_date("2025-01-15T10:00:00Z", "en")
        "Jan 15, 2025, 10:00:00 AM"
        >>> format_date("2025-01-15T10:00:00Z", "de")
        "15.01.2025, 10:00:00"
        >>> format_date("2025-01-15", "en")
        "January 15, 2025"
    """
    if not date_string:
        return date_string

    # Try to parse the date
    parsed = parse_date(date_string)
    if parsed is None:
        # Return original string if parsing fails
        return date_string

    # Determine if we have time information
    # Check if the datetime has non-zero time components
    has_time = (
        parsed.hour != 0 or
        parsed.minute != 0 or
        parsed.second != 0
    )

    try:
        if has_time:
            # Format with date and time using locale's default format
            formatted = format_datetime(
                parsed,
                format='medium',  # Locale-default medium format
                locale=language
            )
        else:
            # Format date only using locale's default format
            formatted = babel_format_date(
                parsed,
                format='long',  # Locale-default long format for better readability
                locale=language
            )

        return formatted
    except (ValueError, AttributeError, UnknownLocaleError):
        # If babel formatting fails (e.g., unknown locale), return original
        return date_string
