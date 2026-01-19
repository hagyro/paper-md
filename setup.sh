#!/bin/bash
# Paper MD - One-command setup script
# Usage: curl -sSL https://raw.githubusercontent.com/hagyro/paper-md/main/setup.sh | bash

set -e

echo "=========================================="
echo "  Paper MD - Academic PDF to Markdown"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check OS
OS="$(uname -s)"
echo "Detected OS: $OS"

# Step 1: Install uv if not present
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing uv (Python package manager)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}✓ uv installed${NC}"
else
    echo -e "${GREEN}✓ uv already installed${NC}"
fi

# Step 2: Install Ollama if not present (for free local AI)
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Installing Ollama (local AI for figure descriptions)...${NC}"
    if [ "$OS" = "Darwin" ]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Please install Ollama manually: https://ollama.ai/download"
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Please install Ollama manually: https://ollama.ai/download"
        exit 1
    fi
    echo -e "${GREEN}✓ Ollama installed${NC}"
else
    echo -e "${GREEN}✓ Ollama already installed${NC}"
fi

# Step 3: Clone repo if not in it
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}Cloning paper-md repository...${NC}"
    git clone https://github.com/hagyro/paper-md.git
    cd paper-md
    echo -e "${GREEN}✓ Repository cloned${NC}"
fi

# Step 4: Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
uv sync
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 5: Create .env file if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env configuration...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Configuration created${NC}"
fi

# Step 6: Start Ollama service and pull model
echo -e "${YELLOW}Starting Ollama and downloading AI model (this may take a few minutes)...${NC}"
ollama serve &> /dev/null &
sleep 3
ollama pull llava 2>/dev/null || true
echo -e "${GREEN}✓ AI model ready${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "To start the web app, run:"
echo ""
echo -e "  ${YELLOW}uv run uvicorn src.paper_md.main:app --host 0.0.0.0 --port 8000${NC}"
echo ""
echo "Then open: http://localhost:8000"
echo ""
echo "Drag and drop a PDF to convert it to Markdown!"
echo ""
