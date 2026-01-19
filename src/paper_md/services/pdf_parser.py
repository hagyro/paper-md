"""PDF parsing service using PyMuPDF."""

import base64
import logging
from pathlib import Path

import fitz  # PyMuPDF

from ..models import (
    ImageData,
    PageData,
    PDFDocument,
    TableData,
    TextBlock,
)

logger = logging.getLogger(__name__)


def extract_pdf(file_path: Path) -> PDFDocument:
    """Extract text, images, and layout from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        PDFDocument with extracted content.
    """
    doc = fitz.open(file_path)

    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_data = _extract_page(page, page_num)
        pages.append(page_data)

    doc.close()

    return PDFDocument(
        filename=file_path.name,
        total_pages=len(pages),
        pages=pages,
    )


def _extract_page(page: fitz.Page, page_num: int) -> PageData:
    """Extract all content from a single page."""
    # Detect tables first so we can exclude their regions from text extraction
    tables = _detect_tables(page, page_num)
    table_bboxes = [t.bbox for t in tables]

    # Extract text blocks, excluding table regions
    text_blocks = _extract_text_blocks(page, page_num, table_bboxes)
    images = _extract_images(page, page_num)

    return PageData(
        page_num=page_num,
        width=page.rect.width,
        height=page.rect.height,
        text_blocks=text_blocks,
        images=images,
        tables=tables,
    )


def _is_inside_bbox(inner_bbox: tuple, outer_bbox: tuple, threshold: float = 0.5) -> bool:
    """Check if inner_bbox is mostly inside outer_bbox."""
    ix0, iy0, ix1, iy1 = inner_bbox
    ox0, oy0, ox1, oy1 = outer_bbox

    # Calculate intersection
    inter_x0 = max(ix0, ox0)
    inter_y0 = max(iy0, oy0)
    inter_x1 = min(ix1, ox1)
    inter_y1 = min(iy1, oy1)

    if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
        return False

    inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
    inner_area = (ix1 - ix0) * (iy1 - iy0)

    if inner_area <= 0:
        return False

    return (inter_area / inner_area) >= threshold


def _extract_text_blocks(
    page: fitz.Page, page_num: int, exclude_bboxes: list[tuple] = None
) -> list[TextBlock]:
    """Extract text blocks with position and font metadata."""
    blocks = []
    exclude_bboxes = exclude_bboxes or []

    # Get text with detailed information
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # Skip non-text blocks
            continue

        bbox = tuple(block.get("bbox", (0, 0, 0, 0)))

        # Skip if this block is inside a table region
        if any(_is_inside_bbox(bbox, table_bbox) for table_bbox in exclude_bboxes):
            continue

        block_text = ""
        font_size = 0.0
        font_name = ""
        is_bold = False

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                block_text += span.get("text", "")
                # Use the largest font in the block
                span_size = span.get("size", 0)
                if span_size > font_size:
                    font_size = span_size
                    font_name = span.get("font", "")
                    # Check if font name contains "Bold"
                    is_bold = "bold" in font_name.lower()
            block_text += "\n"

        block_text = block_text.strip()
        if not block_text:
            continue

        blocks.append(
            TextBlock(
                text=block_text,
                page_num=page_num,
                bbox=bbox,
                font_size=font_size,
                font_name=font_name,
                is_bold=is_bold,
            )
        )

    return blocks


def _extract_images(page: fitz.Page, page_num: int) -> list[ImageData]:
    """Extract images from a page as base64-encoded data."""
    images = []
    image_list = page.get_images(full=True)

    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]

        try:
            base_image = page.parent.extract_image(xref)
            if not base_image:
                continue

            image_bytes = base_image.get("image")
            if not image_bytes:
                continue

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # Get image position on page
            for img_rect in page.get_image_rects(xref):
                bbox = (img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1)
                break
            else:
                bbox = (0, 0, 0, 0)

            images.append(
                ImageData(
                    image_base64=image_base64,
                    page_num=page_num,
                    bbox=bbox,
                    width=base_image.get("width", 0),
                    height=base_image.get("height", 0),
                    image_index=img_index,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to extract image {img_index} on page {page_num}: {e}")
            continue

    return images


def _detect_tables(page: fitz.Page, page_num: int) -> list[TableData]:
    """Detect tables using PyMuPDF's table finder."""
    tables = []

    try:
        # Use PyMuPDF's table finder
        table_finder = page.find_tables()

        for table in table_finder:
            bbox = table.bbox
            # Extract table content
            content = []
            for row in table.extract():
                # Clean up cells - replace None with empty string, strip whitespace
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        # Clean the cell text
                        cell_text = str(cell).strip()
                        # Replace newlines with spaces
                        cell_text = " ".join(cell_text.split())
                        cleaned_row.append(cell_text)
                content.append(cleaned_row)

            # Only add if table has meaningful content
            if content and len(content) > 1:
                tables.append(
                    TableData(
                        page_num=page_num,
                        bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                        content=content,
                    )
                )
                logger.debug(f"Found table on page {page_num} with {len(content)} rows")

    except AttributeError:
        logger.debug("Table detection not available in this PyMuPDF version")
    except Exception as e:
        logger.warning(f"Table detection failed on page {page_num}: {e}")

    return tables
