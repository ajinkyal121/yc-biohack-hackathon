import os
from models import ResearchContext, Hypothesis, ExperimentResult, Interpretation
from services.claude import call_claude

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "interpret.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


async def interpret_results(
    results: list[ExperimentResult],
    hypotheses: list[Hypothesis],
    context: ResearchContext,
) -> Interpretation:
    """Step 6: Have Claude interpret simulation results and decide next action."""

    # Build a summary of hypotheses and their results
    results_by_hypothesis: dict[int, list[ExperimentResult]] = {}
    for r in results:
        # Match result to hypothesis by job_name prefix
        for h in hypotheses:
            if f"hypothesis_{h.rank}" in r.job_name:
                results_by_hypothesis.setdefault(h.rank, []).append(r)
                break

    # Focus on the top hypothesis with results
    top_hypothesis = hypotheses[0] if hypotheses else None
    top_results = results_by_hypothesis.get(
        top_hypothesis.rank if top_hypothesis else 1, results
    )

    results_text = "\n\n".join(
        f"Job: {r.job_name}\n"
        f"Status: {r.status}\n"
        f"Results: {r.results}\n"
        f"Error: {r.error}" if r.error else
        f"Job: {r.job_name}\n"
        f"Status: {r.status}\n"
        f"Results: {r.results}"
        for r in top_results
    )

    user_content = (
        f"Hypothesis being tested: {top_hypothesis.hypothesis if top_hypothesis else 'N/A'}\n"
        f"Reasoning: {top_hypothesis.reasoning if top_hypothesis else 'N/A'}\n\n"
        f"Experiment results:\n{results_text}\n\n"
        f"Scientist's original question: {context.open_question}\n"
        f"Iteration: {len(context.previous_results) + 1}"
    )

    system_prompt = _load_prompt()
    raw = await call_claude(system_prompt, user_content)

    return Interpretation(
        hypothesis=raw.get("hypothesis", ""),
        verdict=raw.get("verdict", "INCONCLUSIVE"),
        confidence=raw.get("confidence", "low"),
        reasoning=raw.get("reasoning", ""),
        limitations=raw.get("limitations", []),
        next_action=raw.get("next_action", "report"),
        next_experiment=raw.get("next_experiment"),
    )
