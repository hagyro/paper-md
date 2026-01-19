# Academic PDF to Markdown Converter - Implementation Plan

## Overview
Build a FastAPI web service that converts academic papers (PDF) to comprehensive Markdown files, preserving all context including AI-generated descriptions of figures and images.

## Implementation Tasks

### Step 1: Project Setup
- [x] Create pyproject.toml with all dependencies
- [x] Create .env.example with environment variables template
- [x] Create project directory structure (src/paper_md/*, tests/*, data/*)

### Step 2: Core Configuration
- [x] Create src/paper_md/__init__.py
- [x] Create src/paper_md/config.py (settings & environment config)
- [x] Create src/paper_md/models.py (Pydantic models)

### Step 3: PDF Parser Service
- [x] Create src/paper_md/services/__init__.py
- [x] Create src/paper_md/services/pdf_parser.py (PyMuPDF extraction)

### Step 4: Structure Analysis Service
- [x] Create src/paper_md/services/structure.py (section/header detection)

### Step 5: Metadata Extraction Service
- [x] Create src/paper_md/services/metadata.py (title, authors, abstract, refs)

### Step 6: Vision Service
- [x] Create src/paper_md/services/vision.py (OpenAI GPT-4V integration)

### Step 7: Markdown Generator Service
- [x] Create src/paper_md/services/markdown.py (assemble final output)

### Step 8: Background Processor
- [x] Create src/paper_md/workers/__init__.py
- [x] Create src/paper_md/workers/processor.py (async job handling)

### Step 9: API Routes
- [x] Create src/paper_md/api/__init__.py
- [x] Create src/paper_md/api/routes.py (FastAPI endpoints)
- [x] Create src/paper_md/main.py (FastAPI app entry point)

### Step 10: Utilities
- [x] Create src/paper_md/utils/__init__.py
- [x] Create src/paper_md/utils/helpers.py (utility functions)

### Step 11: Testing
- [x] Create tests/__init__.py
- [x] Create tests/test_api.py (basic API tests)

### Step 12: Documentation & Verification
- [x] Create README.md with usage instructions
- [x] Verify server starts correctly
- [x] Test health endpoint

---

## Review Section

### Summary of Changes
Implemented a complete FastAPI web service for converting academic PDFs to Markdown.

### Files Created

| File | Description |
|------|-------------|
| `pyproject.toml` | Project configuration with dependencies |
| `.env.example` | Environment variables template |
| `README.md` | Usage documentation |
| `src/paper_md/__init__.py` | Package init |
| `src/paper_md/config.py` | Pydantic Settings configuration |
| `src/paper_md/models.py` | All Pydantic data models |
| `src/paper_md/main.py` | FastAPI app with lifespan handlers |
| `src/paper_md/api/__init__.py` | API package init |
| `src/paper_md/api/routes.py` | API endpoints (POST /convert, GET /status, GET /result, GET /health) |
| `src/paper_md/services/__init__.py` | Services package init |
| `src/paper_md/services/pdf_parser.py` | PyMuPDF-based PDF extraction |
| `src/paper_md/services/structure.py` | Document structure analysis |
| `src/paper_md/services/metadata.py` | Academic metadata extraction |
| `src/paper_md/services/vision.py` | OpenAI GPT-4V figure descriptions |
| `src/paper_md/services/markdown.py` | Markdown generation |
| `src/paper_md/workers/__init__.py` | Workers package init |
| `src/paper_md/workers/processor.py` | Background job processor |
| `src/paper_md/utils/__init__.py` | Utils package init |
| `src/paper_md/utils/helpers.py` | Utility functions |
| `tests/__init__.py` | Tests package init |
| `tests/test_api.py` | API endpoint tests |

### Key Features Implemented
1. **PDF Parsing**: Extracts text blocks, images, and tables using PyMuPDF
2. **Structure Analysis**: Detects sections, headers, and figure references
3. **Metadata Extraction**: Extracts title, authors, abstract, keywords, references
4. **AI Figure Descriptions**: Integrates with OpenAI GPT-4o for detailed figure descriptions
5. **Markdown Generation**: Produces structured Markdown with YAML frontmatter
6. **Async Job Processing**: Background processing with status polling
7. **RESTful API**: Clean endpoints for conversion workflow

### Verification
- All 5 API tests pass
- Server imports and starts correctly
- Health endpoint responds with `{"status": "healthy"}`

### Usage
```bash
# Install
uv sync

# Run server
uv run uvicorn paper_md.main:app --reload

# Run tests
uv run pytest tests/ -v
```
