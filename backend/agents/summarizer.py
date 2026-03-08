import asyncio
import logging
import os

from models import ResearchContext, PaperInfo, PaperSummary
from services.claude import call_claude

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "summarize.txt")

MAX_CONCURRENT = 3
MAX_PDF_BASE64_CHARS = 20_000_000  # ~15 MB PDF ≈ ~150K tokens; skip larger ones


def _load_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


def _build_single_paper_blocks(paper: PaperInfo, context: ResearchContext) -> list[dict]:
    """Build content blocks for a single paper."""
    blocks: list[dict] = [
        {"type": "text", "text": (
            f"Research context: {context.goal}\n"
            f"Target: {context.target_protein} {context.mutation}\n"
            f"Open question: {context.open_question}\n\n"
            f"Please summarize the following paper:"
        )}
    ]

    if paper.pdf_base64 and len(paper.pdf_base64) <= MAX_PDF_BASE64_CHARS:
        blocks.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": paper.pdf_base64,
            },
        })
        blocks.append({
            "type": "text",
            "text": f"The above PDF is: DOI {paper.doi} - {paper.title}",
        })
    else:
        if paper.pdf_base64:
            logger.warning("PDF too large (%d chars), falling back to abstract for %s",
                           len(paper.pdf_base64), paper.doi)
        blocks.append({
            "type": "text",
            "text": (
                f"Paper DOI: {paper.doi}\n"
                f"Title: {paper.title}\n"
                f"Abstract: {paper.abstract}\n"
                "(Full PDF not available — summarize from abstract)"
            ),
        })

    return blocks


async def _summarize_one(paper: PaperInfo, context: ResearchContext,
                         system_prompt: str, semaphore: asyncio.Semaphore) -> list[dict]:
    """Summarize a single paper with concurrency control."""
    async with semaphore:
        try:
            blocks = _build_single_paper_blocks(paper, context)
            result = await call_claude(system_prompt, blocks)
            if isinstance(result, dict):
                return [result]
            return result
        except Exception as e:
            logger.error("Failed to summarize paper %s: %s", paper.doi, e)
            if paper.pdf_base64:
                logger.info("Retrying %s with abstract only", paper.doi)
                fallback_blocks = [
                    {"type": "text", "text": (
                        f"Research context: {context.goal}\n"
                        f"Target: {context.target_protein} {context.mutation}\n"
                        f"Open question: {context.open_question}\n\n"
                        f"Please summarize the following paper:"
                    )},
                    {"type": "text", "text": (
                        f"Paper DOI: {paper.doi}\n"
                        f"Title: {paper.title}\n"
                        f"Abstract: {paper.abstract}\n"
                        "(Full PDF not available — summarize from abstract)"
                    )},
                ]
                try:
                    result = await call_claude(system_prompt, fallback_blocks)
                    if isinstance(result, dict):
                        return [result]
                    return result
                except Exception as retry_err:
                    logger.error("Retry also failed for %s: %s", paper.doi, retry_err)
            return []


async def run_summarization(context: ResearchContext) -> list[PaperSummary]:
    """Step 2: Summarize retrieved papers using Claude.

    Processes each paper individually to stay within token limits.
    Filters out papers with relevance_score < 0.7.
    """
    relevant_papers = [p for p in context.papers if p.relevance_score >= 0.7]
    if not relevant_papers:
        relevant_papers = sorted(context.papers, key=lambda p: p.relevance_score, reverse=True)[:3]

    if not relevant_papers:
        return []

    system_prompt = _load_prompt()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [
        _summarize_one(paper, context, system_prompt, semaphore)
        for paper in relevant_papers
    ]
    all_raw = await asyncio.gather(*tasks)

    summaries = []
    for raw_list in all_raw:
        for s in raw_list:
            summaries.append(PaperSummary(
                paper_doi=s.get("paper_doi", ""),
                target=s.get("target", ""),
                finding=s.get("finding", ""),
                method=s.get("method", ""),
                pdb_available=s.get("pdb_available", False),
                pdb_id=s.get("pdb_id"),
                open_questions=s.get("open_questions", []),
            ))

    return summaries
