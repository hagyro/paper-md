"""Pydantic models for request/response and internal data structures."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# Job Status Models
# ============================================================

class JobStatus(str, Enum):
    """Status of a conversion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobResponse(BaseModel):
    """Response when a job is created."""

    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: JobStatus
    progress: float = Field(ge=0.0, le=1.0, description="Progress from 0 to 1")
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"


# ============================================================
# PDF Document Models
# ============================================================

class TextBlock(BaseModel):
    """A block of text extracted from PDF."""

    text: str
    page_num: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    font_size: float = 0.0
    font_name: str = ""
    is_bold: bool = False


class ImageData(BaseModel):
    """Image extracted from PDF."""

    image_base64: str
    page_num: int
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    image_index: int


class TableData(BaseModel):
    """Table detected in PDF."""

    page_num: int
    bbox: tuple[float, float, float, float]
    content: list[list[str]] = Field(default_factory=list)


class PageData(BaseModel):
    """Data extracted from a single PDF page."""

    page_num: int
    width: float
    height: float
    text_blocks: list[TextBlock] = Field(default_factory=list)
    images: list[ImageData] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)


class PDFDocument(BaseModel):
    """Complete extracted PDF document."""

    filename: str
    total_pages: int
    pages: list[PageData] = Field(default_factory=list)


# ============================================================
# Document Structure Models
# ============================================================

class SectionType(str, Enum):
    """Type of document section."""

    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    OTHER = "other"


class Section(BaseModel):
    """A section of the document."""

    title: str
    section_type: SectionType = SectionType.OTHER
    level: int = 1  # Heading level (1 = H1, 2 = H2, etc.)
    content: str = ""
    page_start: int = 0
    page_end: int = 0
    subsections: list["Section"] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    """Analyzed structure of the document."""

    sections: list[Section] = Field(default_factory=list)
    figure_references: dict[str, int] = Field(default_factory=dict)


# ============================================================
# Metadata Models
# ============================================================

class Author(BaseModel):
    """Paper author information."""

    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


class Citation(BaseModel):
    """A citation/reference."""

    index: int
    raw_text: str
    authors: Optional[str] = None
    title: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None


class PaperMetadata(BaseModel):
    """Academic paper metadata."""

    title: str = ""
    authors: list[Author] = Field(default_factory=list)
    abstract: str = ""
    keywords: list[str] = Field(default_factory=list)
    references: list[Citation] = Field(default_factory=list)


# ============================================================
# Figure Description Models
# ============================================================

class FigureDescription(BaseModel):
    """AI-generated description of a figure."""

    image_index: int
    page_num: int
    figure_type: str = ""  # graph, diagram, photo, table, etc.
    description: str = ""
    caption: Optional[str] = None


# ============================================================
# Processing Result Models
# ============================================================

class ConversionResult(BaseModel):
    """Result of PDF to Markdown conversion."""

    markdown: str
    metadata: PaperMetadata
    figures_described: int = 0
    pages_processed: int = 0
