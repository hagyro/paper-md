# Paper MD

Academic PDF to Markdown converter with AI-powered figure descriptions.

## Quick Start (One Command)

**macOS/Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/hagyro/paper-md/main/setup.sh | bash
```

This automatically installs everything you need:
- `uv` (Python package manager)
- `Ollama` (local AI for figure descriptions - free, no API key needed)
- `LLaVA` model (vision AI)
- All Python dependencies

After setup, start the app:
```bash
cd paper-md
./run.sh
```

Then open **http://localhost:8000** and drag & drop a PDF!

---

## Manual Installation

If you prefer manual setup:

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [Ollama](https://ollama.ai) (for free local AI)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/hagyro/paper-md.git
cd paper-md

# 2. Install dependencies
uv sync

# 3. Install Ollama and pull the vision model
brew install ollama  # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh  # Linux

ollama serve &
ollama pull llava

# 4. Create config file
cp .env.example .env

# 5. Run the app
./run.sh
# or: uv run uvicorn src.paper_md.main:app --host 0.0.0.0 --port 8000
```

---

## Features

- **Web Interface** - Drag & drop PDF upload at http://localhost:8000
- **AI Figure Descriptions** - Automatic descriptions for charts, graphs, diagrams
- **Metadata Extraction** - Title, authors, abstract, keywords, references
- **Document Structure** - Preserves sections, subsections, headings
- **Multiple AI Providers** - Ollama (free), OpenAI, Google Gemini

## Configuration

Edit `.env` to customize:

```bash
# Vision Provider: ollama (free), openai, gemini, none
VISION_PROVIDER=ollama

# For OpenAI (optional)
OPENAI_API_KEY=sk-...

# For Google Gemini (optional, free tier available)
GEMINI_API_KEY=...

# Table extraction via vision (requires good model like GPT-4V)
ENABLE_TABLE_VISION=false
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check |
| `/convert` | POST | Upload PDF, returns job_id |
| `/status/{job_id}` | GET | Check conversion progress |
| `/result/{job_id}` | GET | Download markdown result |

### Example API Usage

```bash
# Upload PDF
curl -X POST -F "file=@paper.pdf" http://localhost:8000/convert
# Returns: {"job_id": "abc-123", "status": "processing"}

# Check status
curl http://localhost:8000/status/abc-123
# Returns: {"job_id": "abc-123", "status": "completed", "progress": 1.0}

# Download result
curl http://localhost:8000/result/abc-123 -o output.md
```

## Project Structure

```
paper-md/
├── setup.sh              # One-command installer
├── run.sh                # Start the app
├── pyproject.toml        # Dependencies
├── .env.example          # Configuration template
└── src/paper_md/
    ├── main.py           # FastAPI app
    ├── config.py         # Settings
    ├── models.py         # Data models
    ├── api/routes.py     # API endpoints
    ├── services/
    │   ├── pdf_parser.py # PDF extraction
    │   ├── vision.py     # AI figure descriptions
    │   └── markdown.py   # Markdown generation
    ├── workers/
    │   └── processor.py  # Background processing
    └── static/
        └── index.html    # Web interface
```

## Development

```bash
# Run tests
uv run pytest

# Run linter
uv run ruff check src tests

# Format code
uv run ruff format src tests
```

## Troubleshooting

**Ollama not running:**
```bash
ollama serve &
```

**Port already in use:**
```bash
lsof -ti :8000 | xargs kill -9
./run.sh
```

**Slow figure descriptions:**
- LLaVA model needs ~4GB RAM
- First run downloads the model (~4GB)
- Each figure takes 10-30 seconds

## License

MIT
