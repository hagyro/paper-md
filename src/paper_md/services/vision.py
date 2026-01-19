"""Vision service for AI-powered figure description using multiple providers."""

import asyncio
import base64
import logging
import httpx

from ..config import get_settings, VisionProvider
from ..models import FigureDescription, ImageData, TableData

logger = logging.getLogger(__name__)

# Prompt template for figure description
FIGURE_PROMPT = """You are analyzing a figure from an academic paper.

Paper context: {paper_title}
{abstract_snippet}

Describe this figure in detail including:
1. What type of visualization it is (graph, diagram, photo, flowchart, table, etc.)
2. All visible data, labels, axes, legends
3. Key findings or patterns shown
4. How it relates to the paper's argument
5. Any notable features or annotations

Provide a comprehensive description that would allow someone to understand the figure without seeing it.

Format your response as:
TYPE: [type of visualization]
DESCRIPTION: [detailed description]"""

# Prompt template for table extraction
TABLE_PROMPT = """You are analyzing a table from an academic paper.

Extract this table and format it as a proper markdown table.
- Include ALL data visible in the table
- Preserve the exact values, numbers, and text
- Include any statistical significance markers (*, **, ***)
- Include column headers and row labels
- Use proper markdown table syntax with | separators
- If there are multiple panels (Panel A, Panel B), format each separately

Important: Return ONLY the markdown table(s), no additional explanation.
If you cannot read the table clearly, describe what you can see."""


async def describe_figures(
    images: list[ImageData],
    paper_title: str = "",
    abstract: str = "",
) -> list[FigureDescription]:
    """Generate descriptions for all figures using configured vision provider.

    Args:
        images: List of extracted images.
        paper_title: Title of the paper for context.
        abstract: Abstract snippet for context.

    Returns:
        List of FigureDescription objects.
    """
    settings = get_settings()

    if settings.vision_provider == VisionProvider.NONE:
        logger.info("Vision provider set to NONE, skipping figure descriptions")
        return _create_unavailable_descriptions(images, "Vision disabled")

    if settings.vision_provider == VisionProvider.OPENAI:
        return await _describe_with_openai(images, paper_title, abstract)
    elif settings.vision_provider == VisionProvider.OLLAMA:
        return await _describe_with_ollama(images, paper_title, abstract)
    elif settings.vision_provider == VisionProvider.GEMINI:
        return await _describe_with_gemini(images, paper_title, abstract)
    else:
        return _create_unavailable_descriptions(images, "Unknown provider")


def _create_unavailable_descriptions(
    images: list[ImageData], reason: str
) -> list[FigureDescription]:
    """Create placeholder descriptions when vision is unavailable."""
    return [
        FigureDescription(
            image_index=img.image_index,
            page_num=img.page_num,
            figure_type="unknown",
            description=f"[Figure description unavailable - {reason}]",
        )
        for img in images
    ]


async def describe_tables(tables: list[TableData], max_tables: int = 10) -> dict[int, str]:
    """Generate markdown representations for tables using vision.

    Args:
        tables: List of TableData objects with image_base64.
        max_tables: Maximum number of tables to process (default 10).

    Returns:
        Dictionary mapping table index to markdown table string.
    """
    settings = get_settings()
    results = {}

    if settings.vision_provider == VisionProvider.NONE:
        logger.info("Vision provider set to NONE, skipping table extraction")
        return results

    # Filter tables with images and deduplicate by table number
    tables_with_images = [t for t in tables if t.image_base64]
    logger.info(f"Found {len(tables_with_images)} tables with images (max: {max_tables})")

    # Deduplicate by table number
    seen_numbers = set()
    unique_tables = []
    for t in tables_with_images:
        if t.table_number is not None:
            if t.table_number not in seen_numbers:
                seen_numbers.add(t.table_number)
                unique_tables.append(t)
        else:
            unique_tables.append(t)

    # Limit to max_tables
    tables_to_process = unique_tables[:max_tables]
    logger.info(f"Processing {len(tables_to_process)} unique tables")

    for idx, table in enumerate(tables_to_process):
        table_id = table.table_number or (idx + 1)
        logger.info(f"Extracting Table {table_id} via vision ({idx+1}/{len(tables_to_process)})")

        try:
            if settings.vision_provider == VisionProvider.OPENAI:
                markdown = await _extract_table_openai(table)
            elif settings.vision_provider == VisionProvider.OLLAMA:
                markdown = await _extract_table_ollama(table)
            elif settings.vision_provider == VisionProvider.GEMINI:
                markdown = await _extract_table_gemini(table)
            else:
                continue

            results[idx] = markdown
            logger.info(f"Successfully extracted Table {table_id}")
        except Exception as e:
            logger.error(f"Failed to extract Table {table_id}: {e}")
            results[idx] = f"*[Table extraction failed: {str(e)}]*"

    return results


async def _extract_table_openai(table: TableData) -> str:
    """Extract table using OpenAI GPT-4V."""
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TABLE_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{table.image_base64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=2000,
    )

    return response.choices[0].message.content or ""


async def _extract_table_ollama(table: TableData) -> str:
    """Extract table using Ollama with LLaVA."""
    settings = get_settings()

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": TABLE_PROMPT,
                "images": [table.image_base64],
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()

    return result.get("response", "")


async def _extract_table_gemini(table: TableData) -> str:
    """Extract table using Google Gemini."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            params={"key": settings.gemini_api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": TABLE_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": table.image_base64,
                                }
                            },
                        ]
                    }
                ]
            },
        )
        response.raise_for_status()
        result = response.json()

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return str(result)


# ============================================================
# OpenAI Provider
# ============================================================

async def _describe_with_openai(
    images: list[ImageData],
    paper_title: str,
    abstract: str,
) -> list[FigureDescription]:
    """Describe figures using OpenAI GPT-4V."""
    from openai import AsyncOpenAI

    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured")
        return _create_unavailable_descriptions(images, "OpenAI API key not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    descriptions = []

    for img in images:
        try:
            desc = await _openai_describe_single(client, img, paper_title, abstract)
            descriptions.append(desc)
            await asyncio.sleep(0.5)  # Rate limiting
        except Exception as e:
            logger.error(f"OpenAI failed for figure {img.image_index}: {e}")
            descriptions.append(
                FigureDescription(
                    image_index=img.image_index,
                    page_num=img.page_num,
                    figure_type="unknown",
                    description=f"[Description failed: {str(e)}]",
                )
            )

    return descriptions


async def _openai_describe_single(
    client,
    image: ImageData,
    paper_title: str,
    abstract: str,
) -> FigureDescription:
    """Describe a single figure using OpenAI."""
    prompt = _build_prompt(paper_title, abstract)
    image_format = _detect_image_format(image.image_base64)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image.image_base64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    content = response.choices[0].message.content or ""
    figure_type, description = _parse_vision_response(content)

    return FigureDescription(
        image_index=image.image_index,
        page_num=image.page_num,
        figure_type=figure_type,
        description=description,
    )


# ============================================================
# Ollama Provider (Local LLaVA)
# ============================================================

async def _describe_with_ollama(
    images: list[ImageData],
    paper_title: str,
    abstract: str,
) -> list[FigureDescription]:
    """Describe figures using local Ollama with LLaVA."""
    settings = get_settings()
    descriptions = []

    # Check if Ollama is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code != 200:
                raise ConnectionError("Ollama not responding")
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return _create_unavailable_descriptions(
            images, f"Ollama not running at {settings.ollama_base_url}"
        )

    for img in images:
        try:
            desc = await _ollama_describe_single(img, paper_title, abstract)
            descriptions.append(desc)
        except Exception as e:
            logger.error(f"Ollama failed for figure {img.image_index}: {e}")
            descriptions.append(
                FigureDescription(
                    image_index=img.image_index,
                    page_num=img.page_num,
                    figure_type="unknown",
                    description=f"[Description failed: {str(e)}]",
                )
            )

    return descriptions


async def _ollama_describe_single(
    image: ImageData,
    paper_title: str,
    abstract: str,
) -> FigureDescription:
    """Describe a single figure using Ollama."""
    settings = get_settings()
    prompt = _build_prompt(paper_title, abstract)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "images": [image.image_base64],
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()

    content = result.get("response", "")
    figure_type, description = _parse_vision_response(content)

    return FigureDescription(
        image_index=image.image_index,
        page_num=image.page_num,
        figure_type=figure_type,
        description=description,
    )


# ============================================================
# Google Gemini Provider
# ============================================================

async def _describe_with_gemini(
    images: list[ImageData],
    paper_title: str,
    abstract: str,
) -> list[FigureDescription]:
    """Describe figures using Google Gemini."""
    settings = get_settings()

    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured")
        return _create_unavailable_descriptions(images, "Gemini API key not configured")

    descriptions = []

    for img in images:
        try:
            desc = await _gemini_describe_single(img, paper_title, abstract)
            descriptions.append(desc)
            await asyncio.sleep(0.5)  # Rate limiting
        except Exception as e:
            logger.error(f"Gemini failed for figure {img.image_index}: {e}")
            descriptions.append(
                FigureDescription(
                    image_index=img.image_index,
                    page_num=img.page_num,
                    figure_type="unknown",
                    description=f"[Description failed: {str(e)}]",
                )
            )

    return descriptions


async def _gemini_describe_single(
    image: ImageData,
    paper_title: str,
    abstract: str,
) -> FigureDescription:
    """Describe a single figure using Gemini."""
    settings = get_settings()
    prompt = _build_prompt(paper_title, abstract)
    image_format = _detect_image_format(image.image_base64)

    # Map format to MIME type
    mime_map = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(image_format, "image/png")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            params={"key": settings.gemini_api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image.image_base64,
                                }
                            },
                        ]
                    }
                ]
            },
        )
        response.raise_for_status()
        result = response.json()

    # Extract text from Gemini response
    content = ""
    try:
        content = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        content = str(result)

    figure_type, description = _parse_vision_response(content)

    return FigureDescription(
        image_index=image.image_index,
        page_num=image.page_num,
        figure_type=figure_type,
        description=description,
    )


# ============================================================
# Utility Functions
# ============================================================

def _build_prompt(paper_title: str, abstract: str) -> str:
    """Build the prompt for figure description."""
    abstract_snippet = abstract[:500] + "..." if len(abstract) > 500 else abstract
    return FIGURE_PROMPT.format(
        paper_title=paper_title or "Unknown",
        abstract_snippet=f"Abstract: {abstract_snippet}" if abstract_snippet else "",
    )


def _detect_image_format(base64_data: str) -> str:
    """Detect image format from base64 data."""
    try:
        header = base64.b64decode(base64_data[:32])
        if header.startswith(b"\x89PNG"):
            return "png"
        elif header.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        elif header.startswith(b"GIF"):
            return "gif"
        elif header.startswith(b"RIFF") and b"WEBP" in header:
            return "webp"
    except Exception:
        pass
    return "png"


def _parse_vision_response(content: str) -> tuple[str, str]:
    """Parse the vision response into type and description."""
    figure_type = "unknown"
    description = content

    lines = content.strip().split("\n")

    for line in lines:
        if line.upper().startswith("TYPE:"):
            figure_type = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("DESCRIPTION:"):
            desc_start = content.find("DESCRIPTION:")
            if desc_start != -1:
                description = content[desc_start + len("DESCRIPTION:") :].strip()
            break

    return figure_type, description
