# Paper MD

Academic PDF to Markdown converter with AI-powered figure descriptions.

## Features

- Converts academic papers (PDF) to structured Markdown
- Extracts metadata: title, authors, abstract, keywords, references
- AI-generated descriptions for figures using OpenAI GPT-4V
- Preserves document structure (sections, subsections)
- Async processing with job status polling
- Table detection and conversion

## Installation

```bash
# Clone the repository
cd paper_md

# Install dependencies with uv
uv sync

# For development dependencies
uv sync --extra dev
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key for GPT-4V figure descriptions

Optional:
- `MAX_FILE_SIZE_MB` - Maximum PDF file size (default: 50)
- `JOB_TIMEOUT_SECONDS` - Job processing timeout (default: 300)
- `TEMP_DIR` - Temporary file storage (default: /tmp/paper_md)
- `LOG_LEVEL` - Logging level (default: INFO)

## Usage

### Start the server

```bash
uv run uvicorn paper_md.main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Convert PDF
```bash
curl -X POST -F "file=@paper.pdf" http://localhost:8000/convert
```

Returns:
```json
{"job_id": "uuid-here", "status": "processing"}
```

#### Check Status
```bash
curl http://localhost:8000/status/{job_id}
```

Returns:
```json
{"job_id": "uuid-here", "status": "completed", "progress": 1.0}
```

#### Download Result
```bash
curl http://localhost:8000/result/{job_id} -o output.md
```

### Interactive API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Run tests

```bash
uv run pytest
```

### Run linter

```bash
uv run ruff check src tests
```

### Format code

```bash
uv run ruff format src tests
```

## Project Structure

```
paper_md/
├── pyproject.toml              # Project config & dependencies
├── README.md                   # This file
├── .env.example                # Environment variables template
├── src/
│   └── paper_md/
│       ├── __init__.py
│       ├── main.py             # FastAPI app entry point
│       ├── config.py           # Settings & environment config
│       ├── models.py           # Pydantic models
│       ├── api/
│       │   └── routes.py       # API endpoints
│       ├── services/
│       │   ├── pdf_parser.py   # PyMuPDF extraction
│       │   ├── structure.py    # Document structure analysis
│       │   ├── metadata.py     # Academic metadata extraction
│       │   ├── vision.py       # OpenAI GPT-4V integration
│       │   └── markdown.py     # Markdown generation
│       ├── workers/
│       │   └── processor.py    # Background job processor
│       └── utils/
│           └── helpers.py      # Utility functions
├── tests/
│   └── test_api.py             # API tests
└── data/
    └── samples/                # Sample PDFs for testing
```

## License

MIT
