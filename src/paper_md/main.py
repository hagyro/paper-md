"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import get_settings

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Path to static files
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting Paper MD service")

    # Ensure temp directory exists
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory: {settings.temp_dir}")

    # Log vision provider
    logger.info(f"Vision provider: {settings.vision_provider.value}")

    yield

    # Shutdown
    logger.info("Shutting down Paper MD service")


# Create FastAPI app
app = FastAPI(
    title="Paper MD",
    description="Academic PDF to Markdown converter with AI-powered figure descriptions",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    """Serve the main web interface."""
    return FileResponse(STATIC_DIR / "index.html")


# Mount static files (for any additional assets)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
