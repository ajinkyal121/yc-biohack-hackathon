import base64
import os
from datetime import datetime, timedelta

from models import ScientistInput, ResearchContext, PaperInfo
from services.claude import call_claude
from services.biorxiv import search_papers, fetch_paper_pdf
from config import MAX_PAPERS

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "ingestion.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


async def run_ingestion(scientist_input: ScientistInput) -> ResearchContext:
    """Step 1: Parse scientist input, query bioRxiv, download PDFs.

    Returns a ResearchContext with extracted intent and retrieved papers.
    """
    # Build content blocks for Claude
    content_blocks = [{"type": "text", "text": scientist_input.text}]

    # Add any uploaded files
    for file_info in scientist_input.files:
        if file_info["media_type"] == "application/pdf":
            content_blocks.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": file_info["content_base64"],
                },
            })
        else:
            # For text-based files (CSV, FASTA, TXT), decode and add as text
            decoded = base64.b64decode(file_info["content_base64"]).decode("utf-8", errors="replace")
            content_blocks.append({
                "type": "text",
                "text": f"--- File: {file_info['filename']} ---\n{decoded}",
            })

    # Ask Claude to extract structured research context
    system_prompt = _load_prompt()
    parsed = await call_claude(system_prompt, content_blocks)

    context = ResearchContext(
        goal=parsed.get("goal", ""),
        target_protein=parsed.get("target_protein", ""),
        mutation=parsed.get("mutation", ""),
        provided_sequence=parsed.get("provided_sequence", ""),
        known_facts=parsed.get("known_facts", []),
        open_question=parsed.get("open_question", ""),
        search_keywords=parsed.get("search_keywords", []),
        biorxiv_category=parsed.get("biorxiv_category", "biochemistry"),
    )

    # Query bioRxiv
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    raw_papers = await search_papers(
        start_date=start_date,
        end_date=end_date,
        category=context.biorxiv_category,
        keywords=context.search_keywords,
        max_results=MAX_PAPERS,
    )

    # Download PDFs for top papers and score relevance
    papers = []
    for paper_data in raw_papers:
        try:
            pdf_bytes = await fetch_paper_pdf(paper_data["doi"])
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
        except Exception:
            pdf_b64 = None

        papers.append(PaperInfo(
            doi=paper_data["doi"],
            title=paper_data["title"],
            abstract=paper_data["abstract"],
            date=paper_data["date"],
            pdf_base64=pdf_b64,
        ))

    # Score relevance using Claude
    if papers:
        scoring_content = [
            {"type": "text", "text": (
                f"Scientist's question: {context.open_question}\n\n"
                "Score the relevance (0.0 to 1.0) of each paper to this question. "
                "Return a JSON array of objects with 'doi' and 'relevance_score'.\n\n"
                "Papers:\n" + "\n".join(
                    f"- DOI: {p.doi}, Title: {p.title}, Abstract: {p.abstract[:300]}"
                    for p in papers
                )
            )}
        ]
        scores = await call_claude(
            "You are a research relevance scorer. Return only valid JSON.",
            scoring_content,
        )
        score_map = {s["doi"]: s["relevance_score"] for s in scores}
        for p in papers:
            p.relevance_score = score_map.get(p.doi, 0.0)

    context.papers = papers
    return context
