"""Table detection and formatting for text-based tables."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def format_text_tables(text: str) -> str:
    """Detect and format table-like patterns in text.

    This handles cases where tables are extracted as plain text
    with values on separate lines.
    """
    lines = text.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        # Check if this looks like a table header
        table_result = _try_extract_table(lines, i)

        if table_result:
            table_md, end_idx = table_result
            result_lines.append(table_md)
            i = end_idx
        else:
            result_lines.append(lines[i])
            i += 1

    return '\n'.join(result_lines)


def _try_extract_table(lines: list[str], start_idx: int) -> Optional[tuple[str, int]]:
    """Try to extract a table starting at the given index.

    Returns (markdown_table, end_index) if successful, None otherwise.
    """
    if start_idx >= len(lines):
        return None

    # Look for patterns like "Table X." or header rows
    current_line = lines[start_idx].strip()

    # Check for table caption pattern
    table_caption = None
    if re.match(r'^Table\s+\d+', current_line, re.IGNORECASE):
        table_caption = current_line
        start_idx += 1
        if start_idx >= len(lines):
            return None

    # Try to detect column headers
    # Headers are typically short text items on consecutive lines
    header_candidates = []
    idx = start_idx

    # Skip empty lines and panel labels
    while idx < len(lines) and (not lines[idx].strip() or
                                 re.match(r'^Panel\s+[A-Z]\.?', lines[idx].strip(), re.IGNORECASE)):
        if lines[idx].strip():
            # Add panel label to caption
            if table_caption:
                table_caption += " - " + lines[idx].strip()
            else:
                table_caption = lines[idx].strip()
        idx += 1

    if idx >= len(lines):
        return None

    # Collect potential header items
    # Headers are usually short words/phrases
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue

        # If it looks like a year or pure number, we've hit data
        if re.match(r'^\d{4}$', line) or re.match(r'^[\d,\.]+$', line):
            break

        # If it's a short text (likely a column header)
        if len(line) < 30 and not re.match(r'^[\d,\.]+$', line):
            header_candidates.append(line)
            idx += 1
        else:
            break

    if len(header_candidates) < 2:
        return None

    # Now try to collect data rows
    # Each row should have: first column (year/label) + N values
    num_cols = len(header_candidates)
    data_rows = []
    current_row = []

    while idx < len(lines):
        line = lines[idx].strip()

        if not line:
            idx += 1
            continue

        # Check if this is a row label (year, "Total", etc.)
        is_row_label = (re.match(r'^\d{4}$', line) or
                        line.lower() in ['total', 'mean', 'median', 'std', 'average', 'sum'] or
                        re.match(r'^[A-Za-z\s\-\.]+$', line) and len(line) < 30)

        # Check if this is a numeric value
        is_numeric = bool(re.match(r'^[\d,\.\-\+\*]+$', line.replace(' ', '')))

        if is_row_label and current_row:
            # Save previous row if complete
            if len(current_row) == num_cols:
                data_rows.append(current_row)
            current_row = [line]
            idx += 1
        elif is_row_label and not current_row:
            current_row = [line]
            idx += 1
        elif is_numeric and current_row:
            current_row.append(line)
            idx += 1
            # Check if row is complete
            if len(current_row) == num_cols:
                data_rows.append(current_row)
                current_row = []
        elif is_numeric and not current_row:
            # Orphan number - might be part of previous structure
            idx += 1
        else:
            # Non-table content, stop
            break

    # Save last row if complete
    if len(current_row) == num_cols:
        data_rows.append(current_row)

    if len(data_rows) < 2:
        return None

    # Build markdown table
    md_parts = []

    if table_caption:
        md_parts.append(f"\n**{table_caption}**\n")

    # Header row
    md_parts.append("| " + " | ".join(header_candidates) + " |")
    md_parts.append("| " + " | ".join(["---"] * num_cols) + " |")

    # Data rows
    for row in data_rows:
        # Escape pipe characters
        escaped_row = [cell.replace("|", "\\|") for cell in row]
        md_parts.append("| " + " | ".join(escaped_row) + " |")

    md_parts.append("")  # Empty line after table

    logger.info(f"Detected text-based table with {len(data_rows)} rows and {num_cols} columns")

    return '\n'.join(md_parts), idx


def detect_and_format_tables(content: str) -> str:
    """Main entry point for table detection and formatting."""
    # First, try to detect obvious table patterns
    result = format_text_tables(content)
    return result
