#!/bin/bash
# Start Paper MD web app

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &> /dev/null &
    sleep 2
fi

echo "Starting Paper MD at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
uv run uvicorn src.paper_md.main:app --host 0.0.0.0 --port 8000
