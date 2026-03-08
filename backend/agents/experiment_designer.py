import os
from models import ResearchContext, Hypothesis, ExperimentSpec
from services.claude import call_claude

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "experiment_design.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


async def design_experiments(
    hypotheses: list[Hypothesis],
    context: ResearchContext,
) -> list[ExperimentSpec]:
    """Step 4: Translate hypotheses into Tamarind API job specifications."""

    hypotheses_text = "\n\n".join(
        f"Hypothesis {h.rank}: {h.hypothesis}\n"
        f"Reasoning: {h.reasoning}\n"
        f"Validation experiment: {h.validation_experiment}\n"
        f"Tamarind tool: {h.tamarind_tool}\n"
        f"Confidence: {h.confidence}"
        for h in hypotheses
    )

    # Gather available structural data
    structural_data = []
    for p in context.papers:
        if any(s.pdb_available for s in [] ):  # Summaries not passed here, but PDB info is in papers
            pass
    pdb_info = ""
    if context.provided_sequence:
        pdb_info += f"\nProvided sequence: {context.provided_sequence[:100]}..."

    paper_pdb_info = "\n".join(
        f"Paper {p.doi}: PDB {p.pdb_id}" for p in context.papers if p.pdb_id
    )
    if paper_pdb_info:
        pdb_info += f"\nAvailable PDB structures from papers:\n{paper_pdb_info}"

    user_content = (
        f"Hypotheses to design experiments for:\n{hypotheses_text}\n\n"
        f"Research context:\n"
        f"Target: {context.target_protein} {context.mutation}\n"
        f"Goal: {context.goal}"
        f"{pdb_info}"
    )

    system_prompt = _load_prompt()
    raw = await call_claude(system_prompt, user_content)

    return [
        ExperimentSpec(
            job_name=spec.get("job_name", f"job_{i}"),
            type=spec.get("type", ""),
            settings=spec.get("settings", {}),
            hypothesis_rank=spec.get("hypothesis_rank", 0),
        )
        for i, spec in enumerate(raw)
    ]
