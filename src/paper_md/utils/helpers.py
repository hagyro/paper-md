"""Utility helper functions."""

import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to be filesystem-safe.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename.
    """
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")

    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        # Preserve extension if present
        path = Path(sanitized)
        ext = path.suffix
        name = path.stem[: max_length - len(ext) - 1]
        sanitized = name + ext

    return sanitized or "unnamed"


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to add if truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text

    # Try to truncate at a word boundary
    truncated = text[: max_length - len(suffix)]
    last_space = truncated.rfind(" ")

    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.rstrip() + suffix


def clean_text(text: str) -> str:
    """Clean and normalize text.

    Args:
        text: Text to clean.

    Returns:
        Cleaned text.
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove control characters except newlines
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()
