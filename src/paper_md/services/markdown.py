"""Markdown generation service."""

import logging
from typing import Optional

from ..models import (
    ConversionResult,
    DocumentStructure,
    FigureDescription,
    PaperMetadata,
    PDFDocument,
    Section,
    SectionType,
    TableData,
)

logger = logging.getLogger(__name__)


def generate_markdown(
    doc: PDFDocument,
    structure: DocumentStructure,
    metadata: PaperMetadata,
    figure_descriptions: list[FigureDescription],
) -> ConversionResult:
    """Generate Markdown from extracted document data.

    Args:
        doc: Extracted PDF document.
        structure: Analyzed document structure.
        metadata: Extracted paper metadata.
        figure_descriptions: AI-generated figure descriptions.

    Returns:
        ConversionResult with markdown content.
    """
    parts = []

    # Add YAML frontmatter
    frontmatter = _generate_frontmatter(metadata)
    parts.append(frontmatter)

    # Add title
    if metadata.title:
        parts.append(f"# {metadata.title}\n")

    # Add authors if present
    if metadata.authors:
        author_names = [a.name for a in metadata.authors]
        parts.append(f"**Authors:** {', '.join(author_names)}\n")

    # Add abstract
    if metadata.abstract:
        parts.append("## Abstract\n")
        parts.append(f"{metadata.abstract}\n")

    # Add keywords if present
    if metadata.keywords:
        parts.append(f"**Keywords:** {', '.join(metadata.keywords)}\n")

    parts.append("---\n")

    # Add sections
    figure_idx = 0
    for section in structure.sections:
        # Skip title and abstract (already added)
        if section.section_type in [SectionType.TITLE, SectionType.ABSTRACT]:
            continue

        section_md, figure_idx = _render_section(
            section, figure_descriptions, figure_idx
        )
        parts.append(section_md)

    # Add any remaining figures at the end
    if figure_idx < len(figure_descriptions):
        parts.append("\n## Figures\n")
        for fig in figure_descriptions[figure_idx:]:
            parts.append(_render_figure(fig))

    # Add tables
    tables = _collect_tables(doc)
    if tables:
        parts.append("\n## Tables\n")
        for i, table in enumerate(tables):
            parts.append(f"\n### Table {i + 1}\n")
            parts.append(_render_table(table))

    # Add references
    if metadata.references:
        parts.append("\n## References\n")
        for ref in metadata.references:
            parts.append(f"{ref.index}. {ref.raw_text}\n")

    markdown = "\n".join(parts)

    return ConversionResult(
        markdown=markdown,
        metadata=metadata,
        figures_described=len(figure_descriptions),
        pages_processed=doc.total_pages,
    )


def _generate_frontmatter(metadata: PaperMetadata) -> str:
    """Generate YAML frontmatter."""
    lines = ["---"]

    if metadata.title:
        # Escape quotes in title
        title = metadata.title.replace('"', '\\"')
        lines.append(f'title: "{title}"')

    if metadata.authors:
        lines.append("authors:")
        for author in metadata.authors:
            lines.append(f'  - name: "{author.name}"')
            if author.affiliation:
                lines.append(f'    affiliation: "{author.affiliation}"')

    if metadata.keywords:
        keywords_str = ", ".join(metadata.keywords)
        lines.append(f"keywords: [{keywords_str}]")

    lines.append("---\n")

    return "\n".join(lines)


def _render_section(
    section: Section,
    figures: list[FigureDescription],
    current_figure_idx: int,
) -> tuple[str, int]:
    """Render a section to Markdown."""
    parts = []

    # Render heading
    heading_prefix = "#" * min(section.level + 1, 6)  # +1 because title is H1
    parts.append(f"\n{heading_prefix} {section.title}\n")

    # Render content
    if section.content:
        content = section.content.strip()

        # Check for figure references in content and insert descriptions
        content, current_figure_idx = _insert_figure_descriptions(
            content, figures, current_figure_idx
        )

        parts.append(f"{content}\n")

    # Render subsections
    for subsection in section.subsections:
        subsection_md, current_figure_idx = _render_section(
            subsection, figures, current_figure_idx
        )
        parts.append(subsection_md)

    return "\n".join(parts), current_figure_idx


def _insert_figure_descriptions(
    content: str,
    figures: list[FigureDescription],
    current_idx: int,
) -> tuple[str, int]:
    """Insert figure descriptions at appropriate locations in content."""
    import re

    # Find figure references like "Figure 1", "Fig. 2"
    pattern = r"(?:Figure|Fig\.?)\s*(\d+)"
    matches = list(re.finditer(pattern, content, re.IGNORECASE))

    if not matches or current_idx >= len(figures):
        return content, current_idx

    # Insert figure descriptions after their references
    offset = 0
    for match in matches:
        if current_idx >= len(figures):
            break

        fig = figures[current_idx]
        fig_block = _render_figure(fig)

        # Insert after the sentence containing the reference
        insert_pos = match.end()
        # Find end of sentence
        sentence_end = content.find(".", insert_pos)
        if sentence_end != -1 and sentence_end < insert_pos + 100:
            insert_pos = sentence_end + 1

        insert_pos += offset
        content = content[:insert_pos] + "\n\n" + fig_block + "\n" + content[insert_pos:]
        offset += len(fig_block) + 3
        current_idx += 1

    return content, current_idx


def _render_figure(fig: FigureDescription) -> str:
    """Render a figure description as Markdown."""
    parts = [
        f"**Figure {fig.image_index + 1}** (Page {fig.page_num + 1})",
        f"- **Type:** {fig.figure_type}",
        f"- **Description:** {fig.description}",
    ]

    if fig.caption:
        parts.append(f"- **Caption:** {fig.caption}")

    return "\n".join(parts)


def _collect_tables(doc: PDFDocument) -> list[TableData]:
    """Collect all tables from document."""
    tables = []
    for page in doc.pages:
        tables.extend(page.tables)
    return tables


def _render_table(table: TableData) -> str:
    """Render a table as Markdown."""
    if not table.content:
        return "*[Empty table]*\n"

    lines = []

    # Get max columns
    max_cols = max(len(row) for row in table.content) if table.content else 0

    if max_cols == 0:
        return "*[Empty table]*\n"

    # Render header (first row)
    header = table.content[0] if table.content else []
    header = header + [""] * (max_cols - len(header))  # Pad if needed
    lines.append("| " + " | ".join(header) + " |")

    # Render separator
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    # Render data rows
    for row in table.content[1:]:
        row = list(row) + [""] * (max_cols - len(row))  # Pad if needed
        # Escape pipe characters in cell content
        row = [cell.replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"
