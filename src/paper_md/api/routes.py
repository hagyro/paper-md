"""API routes for PDF to Markdown conversion."""

import logging
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from ..config import get_settings
from ..models import HealthResponse, JobResponse, JobStatus, JobStatusResponse
from ..workers.processor import job_processor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@router.post("/convert", response_model=JobResponse)
async def convert_pdf(
    file: Annotated[UploadFile, File(description="PDF file to convert")]
) -> JobResponse:
    """Upload a PDF file for conversion to Markdown.

    Returns a job ID that can be used to check status and retrieve results.
    """
    settings = get_settings()

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF",
        )

    # Check file size
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum of {settings.max_file_size_mb}MB",
        )

    # Ensure temp directory exists
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    # Save file to temp location
    temp_path = settings.temp_dir / f"{file.filename}"

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(contents)

    # Create job
    job_id = await job_processor.create_job(temp_path)

    logger.info(f"Created job {job_id} for file {file.filename}")

    return JobResponse(job_id=job_id, status=JobStatus.PROCESSING)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str) -> JobStatusResponse:
    """Check the status of a conversion job."""
    job = await job_processor.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        error=job.error,
    )


@router.get("/result/{job_id}")
async def get_result(job_id: str) -> PlainTextResponse:
    """Download the markdown result of a completed job."""
    job = await job_processor.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if job.status == JobStatus.FAILED:
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {job.error}",
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=202,
            detail="Job still processing",
        )

    if not job.result:
        raise HTTPException(
            status_code=500,
            detail="Job completed but no result available",
        )

    # Return markdown with appropriate filename header
    filename = Path(job.file_path).stem + ".md"

    return PlainTextResponse(
        content=job.result.markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
