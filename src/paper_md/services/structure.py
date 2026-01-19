"""Document structure analysis service."""

import re
import logging
from statistics import median

from ..models import (
    DocumentStructure,
    PDFDocument,
    Section,
    SectionType,
    TextBlock,
)

logger = logging.getLogger(__name__)

# Common section header patterns in academic papers
SECTION_PATTERNS = {
    SectionType.ABSTRACT: r"^abstract\s*$",
    SectionType.INTRODUCTION: r"^(\d+\.?\s*)?(introduction|background)\s*$",
    SectionType.METHODS: r"^(\d+\.?\s*)?(methods?|methodology|materials?\s*(and|&)\s*methods?)\s*$",
    SectionType.RESULTS: r"^(\d+\.?\s*)?results?\s*$",
    SectionType.DISCUSSION: r"^(\d+\.?\s*)?discussion\s*$",
    SectionType.CONCLUSION: r"^(\d+\.?\s*)?(conclusions?|summary|concluding\s*remarks?)\s*$",
    SectionType.REFERENCES: r"^(references?|bibliography|citations?)\s*$",
    SectionType.APPENDIX: r"^(appendix|appendices|supplementary)\s*",
}


def analyze_structure(doc: PDFDocument) -> DocumentStructure:
    """Analyze document structure to detect sections and hierarchy.

    Args:
        doc: Extracted PDF document.

    Returns:
        DocumentStructure with detected sections.
    """
    # Collect all text blocks
    all_blocks = []
    for page in doc.pages:
        all_blocks.extend(page.text_blocks)

    if not all_blocks:
        return DocumentStructure()

    # Detect headers based on font characteristics
    headers = _detect_headers(all_blocks)

    # Build section hierarchy
    sections = _build_sections(headers, all_blocks)

    # Map figure references
    full_text = "\n".join(block.text for block in all_blocks)
    figure_refs = _map_figure_references(full_text)

    return DocumentStructure(
        sections=sections,
        figure_references=figure_refs,
    )


def _detect_headers(blocks: list[TextBlock]) -> list[TextBlock]:
    """Detect header blocks based on font size and style."""
    if not blocks:
        return []

    # Calculate median font size as baseline
    font_sizes = [b.font_size for b in blocks if b.font_size > 0]
    if not font_sizes:
        return []

    median_size = median(font_sizes)
    max_size = max(font_sizes)

    headers = []
    for block in blocks:
        text = block.text.strip()

        # Skip very long blocks (likely paragraphs)
        if len(text) > 200:
            continue

        # Skip blocks that are mostly numbers/symbols
        if len(re.sub(r"[\d\W]", "", text)) < 3:
            continue

        is_header = False

        # Check if font size is significantly larger than median
        if block.font_size > median_size * 1.1:
            is_header = True

        # Check if bold
        if block.is_bold and len(text) < 100:
            is_header = True

        # Check if matches known section patterns
        for pattern in SECTION_PATTERNS.values():
            if re.match(pattern, text.lower()):
                is_header = True
                break

        # Check for numbered section format (e.g., "1. Introduction")
        if re.match(r"^\d+\.?\s+\w", text):
            is_header = True

        if is_header:
            headers.append(block)

    return headers


def _build_sections(headers: list[TextBlock], all_blocks: list[TextBlock]) -> list[Section]:
    """Build section hierarchy from detected headers."""
    if not headers:
        return []

    # Sort headers by position (page number, then y-coordinate)
    sorted_headers = sorted(headers, key=lambda b: (b.page_num, b.bbox[1]))

    sections = []
    for i, header in enumerate(sorted_headers):
        title = header.text.strip()
        section_type = _classify_section(title)

        # Determine heading level based on font size
        level = _determine_level(header, sorted_headers)

        # Get content between this header and the next
        content = _get_section_content(header, sorted_headers, all_blocks, i)

        # Determine page range
        page_start = header.page_num
        page_end = header.page_num
        if i + 1 < len(sorted_headers):
            page_end = sorted_headers[i + 1].page_num

        sections.append(
            Section(
                title=title,
                section_type=section_type,
                level=level,
                content=content,
                page_start=page_start,
                page_end=page_end,
            )
        )

    return sections


def _classify_section(title: str) -> SectionType:
    """Classify section type based on title."""
    title_lower = title.lower().strip()

    for section_type, pattern in SECTION_PATTERNS.items():
        if re.match(pattern, title_lower):
            return section_type

    return SectionType.OTHER


def _determine_level(header: TextBlock, all_headers: list[TextBlock]) -> int:
    """Determine heading level (1-6) based on font size comparison."""
    if not all_headers:
        return 1

    sizes = sorted(set(h.font_size for h in all_headers), reverse=True)

    try:
        level = sizes.index(header.font_size) + 1
        return min(level, 6)  # Cap at H6
    except ValueError:
        return 2  # Default to H2 if not found


def _get_section_content(
    header: TextBlock,
    all_headers: list[TextBlock],
    all_blocks: list[TextBlock],
    header_index: int,
) -> str:
    """Extract content between this header and the next."""
    # Find blocks between this header and the next
    start_page = header.page_num
    start_y = header.bbox[1]

    if header_index + 1 < len(all_headers):
        end_page = all_headers[header_index + 1].page_num
        end_y = all_headers[header_index + 1].bbox[1]
    else:
        end_page = float("inf")
        end_y = float("inf")

    content_parts = []
    for block in all_blocks:
        # Skip the header itself
        if block.text.strip() == header.text.strip():
            continue

        # Check if block is in range
        in_range = False
        if block.page_num == start_page and block.page_num == end_page:
            # Same page - check y coordinates
            if start_y < block.bbox[1] < end_y:
                in_range = True
        elif block.page_num == start_page:
            if block.bbox[1] > start_y:
                in_range = True
        elif block.page_num == end_page:
            if block.bbox[1] < end_y:
                in_range = True
        elif start_page < block.page_num < end_page:
            in_range = True

        if in_range:
            content_parts.append(block.text)

    return "\n\n".join(content_parts)


def _map_figure_references(text: str) -> dict[str, int]:
    """Find figure references in text (e.g., 'Figure 1', 'Fig. 2')."""
    references = {}

    # Pattern to match figure references
    pattern = r"(?:Figure|Fig\.?)\s*(\d+)"
    matches = re.finditer(pattern, text, re.IGNORECASE)

    for match in matches:
        fig_num = match.group(1)
        key = f"figure_{fig_num}"
        if key not in references:
            references[key] = int(fig_num)

    return references
