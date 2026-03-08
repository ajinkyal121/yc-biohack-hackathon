import httpx
from config import BIORXIV_BASE_URL
import asyncio
import logging

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=15.0),
)

MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


async def _get_with_retry(url: str, **kwargs) -> httpx.Response:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await _client.get(url, **kwargs)
            return resp
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF ** attempt
            logger.warning("bioRxiv request timed out (attempt %d/%d), retrying in %.1fs: %s",
                           attempt, MAX_RETRIES, wait, exc)
            await asyncio.sleep(wait)


async def search_papers(
    start_date: str,
    end_date: str,
    category: str,
    keywords: list[str],
    max_results: int = 5,
) -> list[dict]:
    """Search bioRxiv for papers matching keywords in a date range.

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        category: bioRxiv category (e.g., "biochemistry")
        keywords: List of search terms to match against title + abstract
        max_results: Max papers to return

    Returns:
        List of paper dicts with doi, title, abstract, date, category.
    """
    results = []
    cursor = 0
    max_pages = 3  # Limit API calls

    for _ in range(max_pages):
        url = f"{BIORXIV_BASE_URL}/details/biorxiv/{start_date}/{end_date}/{cursor}"
        resp = await _get_with_retry(url)
        data = resp.json()

        collection = data.get("collection", [])
        if not collection:
            break

        for paper in collection:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            text = f"{title} {abstract}"

            # Score by keyword overlap
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                results.append({
                    "doi": paper.get("doi", ""),
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "date": paper.get("date", ""),
                    "category": paper.get("category", ""),
                    "keyword_score": score,
                })

        cursor += 100
        if len(results) >= max_results * 3:
            break

    # Sort by keyword score descending, take top N
    results.sort(key=lambda x: x["keyword_score"], reverse=True)
    return results[:max_results]


async def fetch_paper_pdf(doi: str) -> bytes:
    """Download a paper PDF from bioRxiv.

    Args:
        doi: The paper DOI (e.g., "10.1101/2026.01.22.578901")

    Returns:
        Raw PDF bytes.
    """
    url = f"https://www.biorxiv.org/content/{doi}v1.full.pdf"
    resp = await _get_with_retry(url, follow_redirects=True)
    resp.raise_for_status()
    # Be polite with rate limiting
    await asyncio.sleep(1)
    return resp.content
