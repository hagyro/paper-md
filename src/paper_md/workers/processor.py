"""Background job processor for PDF conversion."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..models import ConversionResult, JobStatus
from ..services.pdf_parser import extract_pdf
from ..services.structure import analyze_structure
from ..services.metadata import extract_metadata
from ..services.vision import describe_figures
from ..services.markdown import generate_markdown

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a conversion job."""

    job_id: str
    file_path: Path
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    result: Optional[ConversionResult] = None
    error: Optional[str] = None


@dataclass
class JobProcessor:
    """Manages background PDF conversion jobs."""

    jobs: dict[str, Job] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def create_job(self, file_path: Path) -> str:
        """Create a new conversion job.

        Args:
            file_path: Path to the uploaded PDF file.

        Returns:
            Job ID for tracking.
        """
        job_id = str(uuid.uuid4())

        async with self._lock:
            self.jobs[job_id] = Job(
                job_id=job_id,
                file_path=file_path,
                status=JobStatus.PENDING,
            )

        # Start processing in background
        asyncio.create_task(self._process_job(job_id))

        return job_id

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        async with self._lock:
            return self.jobs.get(job_id)

    async def _process_job(self, job_id: str) -> None:
        """Process a PDF conversion job."""
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            await self._update_status(job_id, JobStatus.PROCESSING, 0.0)

            # Step 1: Extract PDF (20%)
            logger.info(f"Job {job_id}: Extracting PDF")
            doc = extract_pdf(job.file_path)
            await self._update_status(job_id, JobStatus.PROCESSING, 0.2)

            # Step 2: Analyze structure (40%)
            logger.info(f"Job {job_id}: Analyzing structure")
            structure = analyze_structure(doc)
            await self._update_status(job_id, JobStatus.PROCESSING, 0.4)

            # Step 3: Extract metadata (50%)
            logger.info(f"Job {job_id}: Extracting metadata")
            metadata = extract_metadata(doc, structure)
            await self._update_status(job_id, JobStatus.PROCESSING, 0.5)

            # Step 4: Describe figures (80%)
            logger.info(f"Job {job_id}: Describing figures")
            all_images = []
            for page in doc.pages:
                all_images.extend(page.images)

            figure_descriptions = await describe_figures(
                images=all_images,
                paper_title=metadata.title,
                abstract=metadata.abstract,
            )
            await self._update_status(job_id, JobStatus.PROCESSING, 0.8)

            # Step 5: Generate markdown (100%)
            logger.info(f"Job {job_id}: Generating markdown")
            result = generate_markdown(
                doc=doc,
                structure=structure,
                metadata=metadata,
                figure_descriptions=figure_descriptions,
            )

            # Update job with result
            async with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.COMPLETED
                    self.jobs[job_id].progress = 1.0
                    self.jobs[job_id].result = result

            logger.info(f"Job {job_id}: Completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id}: Failed with error: {e}")
            async with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.FAILED
                    self.jobs[job_id].error = str(e)

        finally:
            # Cleanup temporary file
            try:
                if job.file_path.exists():
                    job.file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")

    async def _update_status(
        self, job_id: str, status: JobStatus, progress: float
    ) -> None:
        """Update job status and progress."""
        async with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = status
                self.jobs[job_id].progress = progress


# Global processor instance
job_processor = JobProcessor()
