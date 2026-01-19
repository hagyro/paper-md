"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router
from .config import get_settings

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting Paper MD service")

    # Ensure temp directory exists
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory: {settings.temp_dir}")

    # Check OpenAI API key
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured - figure descriptions will be unavailable")

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
