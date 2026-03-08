import os
from models import ResearchContext, PaperSummary, Hypothesis
from services.claude import call_claude

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "hypothesis.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


async def generate_hypotheses(
    summaries: list[PaperSummary],
    context: ResearchContext,
) -> list[Hypothesis]:
    """Step 3: Generate ranked hypotheses from summarized findings."""

    summaries_text = "\n\n".join(
        f"Paper: {s.paper_doi}\n"
        f"Target: {s.target}\n"
        f"Finding: {s.finding}\n"
        f"Method: {s.method}\n"
        f"PDB available: {s.pdb_available} (ID: {s.pdb_id})\n"
        f"Open questions: {', '.join(s.open_questions)}"
        for s in summaries
    )

    # Include previous iteration results if any
    prev_context = ""
    if context.previous_results:
        prev_context = "\n\nPrevious experiment results:\n" + "\n".join(
            f"- {r.get('hypothesis', '')}: {r.get('verdict', '')} ({r.get('reasoning', '')})"
            for r in context.previous_results
        )

    user_content = (
        f"Summarized findings:\n{summaries_text}\n\n"
        f"Scientist's open question: {context.open_question}\n"
        f"Target protein: {context.target_protein} {context.mutation}\n"
        f"Known facts: {', '.join(context.known_facts)}"
        f"{prev_context}"
    )

    system_prompt = _load_prompt()
    raw = await call_claude(system_prompt, user_content)

    return [
        Hypothesis(
            rank=h.get("rank", i + 1),
            hypothesis=h.get("hypothesis", ""),
            reasoning=h.get("reasoning", ""),
            validation_experiment=h.get("validation_experiment", ""),
            tamarind_tool=h.get("tamarind_tool", ""),
            confidence=h.get("confidence", "medium"),
        )
        for i, h in enumerate(raw)
    ]
