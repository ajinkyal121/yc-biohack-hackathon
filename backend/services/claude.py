import asyncio
import json
import logging
import re
import time

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 10

# Global rate-limiter: enforce a minimum gap between API calls so we don't
# burst past the org's per-minute input-token cap.
_MIN_CALL_INTERVAL_SECONDS = 15
_last_call_time: float = 0.0
_call_lock = asyncio.Lock()


def _parse_retry_after(error: anthropic.RateLimitError) -> float | None:
    """Try to extract a useful wait time from the rate-limit error message."""
    msg = str(error)
    match = re.search(r"try again in (\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


async def call_claude(
    system_prompt: str,
    user_content: list | str,
    max_tokens: int = 4096,
) -> dict | list:
    """Call Claude and parse the response as JSON.

    Includes a global rate-limiter that spaces out requests and exponential
    back-off with jitter on 429 responses.
    """
    global _last_call_time

    if isinstance(user_content, str):
        user_content = [{"type": "text", "text": user_content}]

    for attempt in range(MAX_RETRIES):
        # Global throttle — wait if the last call was too recent
        async with _call_lock:
            now = time.monotonic()
            elapsed = now - _last_call_time
            if elapsed < _MIN_CALL_INTERVAL_SECONDS:
                gap = _MIN_CALL_INTERVAL_SECONDS - elapsed
                logger.debug("Throttling: waiting %.1fs before next API call", gap)
                await asyncio.sleep(gap)
            _last_call_time = time.monotonic()

        try:
            response = await client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except anthropic.RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            retry_after = _parse_retry_after(e)
            wait = retry_after if retry_after else INITIAL_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning(
                "Rate limited (attempt %d/%d). Retrying in %.0fs...",
                attempt + 1, MAX_RETRIES, wait,
            )
            await asyncio.sleep(wait)

    response_text = response.content[0].text

    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
