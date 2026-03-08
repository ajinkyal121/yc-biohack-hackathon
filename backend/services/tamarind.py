import httpx
import asyncio
from collections.abc import Callable
from config import TAMARIND_API_KEY, TAMARIND_BASE_URL, POLL_INTERVAL_SECONDS

_client = httpx.AsyncClient(
    base_url=TAMARIND_BASE_URL,
    headers={"x-api-key": TAMARIND_API_KEY},
    timeout=60.0,
)

MAX_POLL_ATTEMPTS = 60  # 30 min at 30s intervals


async def submit_job(job_spec: dict) -> str:
    """Submit a job to the Tamarind API.

    Args:
        job_spec: Dict with jobName, type, settings.

    Returns:
        The job name.
    """
    resp = await _client.post("/submit-job", json=job_spec)
    resp.raise_for_status()
    return job_spec["jobName"]


async def poll_job(
    job_name: str,
    on_status: Callable | None = None,
) -> str:
    """Poll a Tamarind job until completion.

    Args:
        job_name: The job name to poll.
        on_status: Optional callback for status updates.

    Returns:
        Final status string.

    Raises:
        TimeoutError: If job doesn't complete within MAX_POLL_ATTEMPTS.
        RuntimeError: If job fails.
    """
    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = await _client.get("/jobs", params={"jobName": job_name})
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "unknown")
        if on_status:
            elapsed = (attempt + 1) * POLL_INTERVAL_SECONDS
            on_status(f"Job {job_name}: {status} ({elapsed}s elapsed)")

        if status == "completed":
            return status
        if status == "failed":
            raise RuntimeError(f"Tamarind job {job_name} failed: {data}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Tamarind job {job_name} timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")


async def get_result(job_name: str) -> dict:
    """Fetch results for a completed Tamarind job.

    Args:
        job_name: The job name.

    Returns:
        Result payload dict.
    """
    resp = await _client.post("/result", json={"jobName": job_name})
    resp.raise_for_status()
    return resp.json()


async def run_job(
    job_spec: dict,
    on_status: Callable | None = None,
) -> dict:
    """Submit, poll, and return results for a Tamarind job.

    Convenience function combining submit + poll + get_result.
    """
    job_name = await submit_job(job_spec)
    await poll_job(job_name, on_status)
    return await get_result(job_name)
