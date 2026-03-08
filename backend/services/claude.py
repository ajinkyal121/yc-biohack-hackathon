import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def call_claude(
    system_prompt: str,
    user_content: list | str,
    max_tokens: int = 4096,
) -> dict | list:
    """Call Claude and parse the response as JSON.

    Args:
        system_prompt: System-level instructions.
        user_content: Either a string or a list of content blocks
                      (text, base64 documents, etc.)
        max_tokens: Max response tokens.

    Returns:
        Parsed JSON (dict or list).
    """
    if isinstance(user_content, str):
        user_content = [{"type": "text", "text": user_content}]

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    response_text = response.content[0].text

    # Extract JSON from the response — handle markdown code fences
    text = response_text.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` wrapper
        lines = text.split("\n")
        lines = lines[1:]  # remove opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
