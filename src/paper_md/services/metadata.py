"""Academic metadata extraction service."""

import re
import logging

from ..models import (
    Author,
    Citation,
    DocumentStructure,
    PageData,
    PaperMetadata,
    PDFDocument,
    SectionType,
)

logger = logging.getLogger(__name__)


def extract_metadata(doc: PDFDocument, structure: DocumentStructure) -> PaperMetadata:
    """Extract academic metadata from the document.

    Args:
        doc: Extracted PDF document.
        structure: Analyzed document structure.

    Returns:
        PaperMetadata with title, authors, abstract, etc.
    """
    if not doc.pages:
        return PaperMetadata()

    first_page = doc.pages[0]

    title = _extract_title(first_page)
    authors = _extract_authors(first_page, title)
    abstract = _extract_abstract(structure)
    keywords = _extract_keywords(doc, structure)
    references = _extract_references(structure)

    return PaperMetadata(
        title=title,
        authors=authors,
        abstract=abstract,
        keywords=keywords,
        references=references,
    )


def _extract_title(first_page: PageData) -> str:
    """Extract paper title from first page (usually largest font)."""
    if not first_page.text_blocks:
        return ""

    # Find block with largest font size in top portion of page
    title_candidates = []
    page_height = first_page.height

    for block in first_page.text_blocks:
        # Focus on top 40% of page for title
        if block.bbox[1] > page_height * 0.4:
            continue

        # Skip very short or very long text
        text = block.text.strip()
        if len(text) < 5 or len(text) > 300:
            continue

        # Skip text that looks like header/footer
        if _is_header_footer(text):
            continue

        title_candidates.append(block)

    if not title_candidates:
        return ""

    # Sort by font size (descending) and position (top first)
    title_candidates.sort(key=lambda b: (-b.font_size, b.bbox[1]))

    # Take the largest font block
    title = title_candidates[0].text.strip()

    # Clean up title
    title = re.sub(r"\s+", " ", title)
    title = title.strip()

    return title


def _extract_authors(first_page: PageData, title: str) -> list[Author]:
    """Extract author names from first page."""
    authors = []

    if not first_page.text_blocks:
        return authors

    # Find blocks below title but above abstract
    title_block = None
    for block in first_page.text_blocks:
        if block.text.strip() == title:
            title_block = block
            break

    if not title_block:
        return authors

    # Look for author blocks below title
    author_candidates = []
    for block in first_page.text_blocks:
        # Must be below title
        if block.bbox[1] <= title_block.bbox[3]:
            continue

        # Skip if too far down (likely abstract or body)
        if block.bbox[1] > first_page.height * 0.4:
            continue

        text = block.text.strip()

        # Skip if looks like abstract header
        if text.lower().startswith("abstract"):
            break

        # Skip affiliations (often contain university, institute, etc.)
        if _is_affiliation(text):
            continue

        # Skip email addresses
        if "@" in text:
            continue

        author_candidates.append(text)

    # Parse author names from candidates
    for text in author_candidates:
        names = _parse_author_names(text)
        for name in names:
            if name and len(name) > 2:
                authors.append(Author(name=name))

    return authors


def _extract_abstract(structure: DocumentStructure) -> str:
    """Extract abstract from document structure."""
    for section in structure.sections:
        if section.section_type == SectionType.ABSTRACT:
            return section.content.strip()

    # Fallback: look for section titled "Abstract"
    for section in structure.sections:
        if "abstract" in section.title.lower():
            return section.content.strip()

    return ""


def _extract_keywords(doc: PDFDocument, structure: DocumentStructure) -> list[str]:
    """Extract keywords if present."""
    keywords = []

    # Search for keywords in document text
    full_text = ""
    for page in doc.pages[:3]:  # Check first 3 pages only
        for block in page.text_blocks:
            full_text += block.text + "\n"

    # Look for "Keywords:" pattern
    pattern = r"keywords?\s*[:]\s*([^\n]+)"
    match = re.search(pattern, full_text, re.IGNORECASE)

    if match:
        keywords_text = match.group(1)
        # Split by common separators
        for sep in [";", ",", "•", "|"]:
            if sep in keywords_text:
                keywords = [k.strip() for k in keywords_text.split(sep)]
                break
        else:
            keywords = [keywords_text.strip()]

    # Clean up keywords
    keywords = [k for k in keywords if k and len(k) < 50]

    return keywords


def _extract_references(structure: DocumentStructure) -> list[Citation]:
    """Extract and parse references section."""
    references = []

    # Find references section
    refs_content = ""
    for section in structure.sections:
        if section.section_type == SectionType.REFERENCES:
            refs_content = section.content
            break

    if not refs_content:
        return references

    # Split into individual references
    # Try numbered format first: [1], 1., (1)
    ref_texts = re.split(r"\n\s*(?:\[\d+\]|\d+\.|\(\d+\))\s*", refs_content)

    if len(ref_texts) <= 1:
        # Try splitting by double newlines
        ref_texts = refs_content.split("\n\n")

    for i, ref_text in enumerate(ref_texts):
        ref_text = ref_text.strip()
        if not ref_text or len(ref_text) < 10:
            continue

        citation = _parse_citation(i + 1, ref_text)
        if citation:
            references.append(citation)

    return references


def _parse_citation(index: int, text: str) -> Citation:
    """Parse a citation string into structured data."""
    citation = Citation(index=index, raw_text=text)

    # Try to extract year (4 digits in parentheses or standalone)
    year_match = re.search(r"\((\d{4})\)|(?:^|\s)(\d{4})(?:\s|$|\.)", text)
    if year_match:
        citation.year = year_match.group(1) or year_match.group(2)

    # Try to extract DOI
    doi_match = re.search(r"10\.\d{4,}/[^\s]+", text)
    if doi_match:
        citation.doi = doi_match.group(0).rstrip(".,;")

    # Try to extract authors (text before year)
    if year_match:
        authors_part = text[: year_match.start()].strip()
        # Clean up
        authors_part = re.sub(r"^\[\d+\]|\(\d+\)|\d+\.", "", authors_part).strip()
        if authors_part:
            citation.authors = authors_part.rstrip(".,;(")

    return citation


def _is_header_footer(text: str) -> bool:
    """Check if text looks like a header or footer."""
    text_lower = text.lower()

    # Page numbers
    if re.match(r"^\d+$", text.strip()):
        return True

    # Common header/footer patterns
    patterns = [
        r"^page\s+\d+",
        r"^\d+\s+of\s+\d+",
        r"^preprint",
        r"^draft",
        r"^confidential",
    ]

    for pattern in patterns:
        if re.match(pattern, text_lower):
            return True

    return False


def _is_affiliation(text: str) -> bool:
    """Check if text looks like an affiliation."""
    text_lower = text.lower()

    affiliation_keywords = [
        "university",
        "institute",
        "department",
        "faculty",
        "school of",
        "college of",
        "laboratory",
        "research center",
        "centre",
    ]

    return any(kw in text_lower for kw in affiliation_keywords)


def _parse_author_names(text: str) -> list[str]:
    """Parse author names from a text block."""
    names = []

    # Clean up text
    text = re.sub(r"\d+", "", text)  # Remove superscript numbers
    text = re.sub(r"[*†‡§]", "", text)  # Remove footnote markers

    # Split by common separators
    for sep in [",", "and", "&", ";"]:
        if sep in text:
            parts = text.split(sep)
            for part in parts:
                name = part.strip()
                if name and len(name) > 2 and len(name) < 50:
                    names.append(name)
            return names

    # Single author
    text = text.strip()
    if text and len(text) > 2 and len(text) < 50:
        names.append(text)

    return names
