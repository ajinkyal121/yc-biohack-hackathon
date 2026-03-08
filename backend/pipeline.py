import asyncio
import traceback

from models import ScientistInput, PipelineEvent
from agents import ingestion, summarizer, hypothesis, experiment_designer, executor, interpreter
from services.claude import call_claude
from config import MAX_LOOP_ITERATIONS

STEP_NAMES = {
    1: "Research Ingestion",
    2: "Summarize Findings",
    3: "Hypothesis Generation",
    4: "Experiment Design",
    5: "Experiment Execution",
    6: "Result Interpretation",
}


async def emit(queue: asyncio.Queue, step: int | str, status: str, data=None, message: str = ""):
    step_name = STEP_NAMES.get(step, str(step)) if isinstance(step, int) else str(step)
    event = PipelineEvent(
        step=step,
        step_name=step_name,
        status=status,
        data=data,
        message=message,
    )
    await queue.put(event)


async def run_pipeline(
    scientist_input: ScientistInput,
    queue: asyncio.Queue,
    run_id: str,
):
    """Execute the full AI Scientist pipeline with loop support."""
    try:
        # Step 1: Research Ingestion
        await emit(queue, 1, "running", message="Parsing input and querying bioRxiv...")
        context = await ingestion.run_ingestion(scientist_input)
        await emit(queue, 1, "complete", data={
            "goal": context.goal,
            "target_protein": context.target_protein,
            "mutation": context.mutation,
            "open_question": context.open_question,
            "papers_found": len(context.papers),
            "papers": [
                {"doi": p.doi, "title": p.title, "relevance": p.relevance_score}
                for p in context.papers
            ],
        }, message=f"Found {len(context.papers)} relevant papers")

        # Step 2: Summarize Findings
        await emit(queue, 2, "running", message="Summarizing papers with Claude...")
        summaries = await summarizer.run_summarization(context)
        await emit(queue, 2, "complete", data=[s.model_dump() for s in summaries],
                   message=f"Summarized {len(summaries)} papers")

        # Loop: Steps 3-6
        all_interpretations = []
        iteration = 0

        while iteration < MAX_LOOP_ITERATIONS:
            iteration += 1
            loop_msg = f" (iteration {iteration})" if iteration > 1 else ""

            # Step 3: Hypothesis Generation
            await emit(queue, 3, "running", message=f"Generating hypotheses{loop_msg}...")
            hypotheses = await hypothesis.generate_hypotheses(summaries, context)
            await emit(queue, 3, "complete", data=[h.model_dump() for h in hypotheses],
                       message=f"Generated {len(hypotheses)} hypotheses")

            # Step 4: Experiment Design
            await emit(queue, 4, "running", message=f"Designing experiments{loop_msg}...")
            specs = await experiment_designer.design_experiments(hypotheses, context)
            await emit(queue, 4, "complete", data=[s.model_dump() for s in specs],
                       message=f"Designed {len(specs)} experiment(s)")

            # Step 5: Experiment Execution
            await emit(queue, 5, "running", message=f"Running experiments on Tamarind{loop_msg}...")

            async def status_callback(msg: str):
                await emit(queue, 5, "running", message=msg)

            results = await executor.run_experiments(specs, on_status=lambda msg: asyncio.ensure_future(
                emit(queue, 5, "running", message=msg)
            ))
            await emit(queue, 5, "complete", data=[r.model_dump() for r in results],
                       message=f"Completed {len(results)} experiment(s)")

            # Step 6: Result Interpretation
            await emit(queue, 6, "running", message=f"Interpreting results{loop_msg}...")
            interp = await interpreter.interpret_results(results, hypotheses, context)
            all_interpretations.append(interp)
            await emit(queue, 6, "complete", data=interp.model_dump(),
                       message=f"Verdict: {interp.verdict} ({interp.confidence})")

            # Check loop condition
            if interp.next_action == "report":
                break

            # Feed back for next iteration
            context.previous_results.append(interp.model_dump())
            await emit(queue, 6, "running",
                       message=f"Looping back for iteration {iteration + 1}: {interp.next_experiment}")

        # Generate final report
        await emit(queue, "final", "running", message="Generating final report...")
        report = await _generate_final_report(context, all_interpretations)
        await emit(queue, "final", "done", data=report, message="Pipeline complete")

    except Exception as e:
        tb = traceback.format_exc()
        await emit(queue, "final", "error", message=f"Pipeline failed: {str(e)}\n{tb}")


async def _generate_final_report(context, interpretations) -> str:
    """Generate a markdown final report summarizing all findings."""
    interp_text = "\n\n".join(
        f"### Hypothesis: {interp.hypothesis}\n"
        f"**Verdict:** {interp.verdict} (Confidence: {interp.confidence})\n"
        f"**Reasoning:** {interp.reasoning}\n"
        f"**Limitations:** {', '.join(interp.limitations)}"
        for interp in interpretations
    )

    prompt = (
        f"Generate a concise markdown research report summarizing these findings.\n\n"
        f"Research goal: {context.goal}\n"
        f"Target: {context.target_protein} {context.mutation}\n"
        f"Open question: {context.open_question}\n\n"
        f"Results:\n{interp_text}\n\n"
        f"Include:\n"
        f"1. Executive Summary (2-3 sentences)\n"
        f"2. Key Findings (one section per hypothesis)\n"
        f"3. Limitations\n"
        f"4. Recommended Next Steps (for wet lab validation)\n\n"
        f"Write in clear scientific prose. Use markdown formatting."
    )

    result = await call_claude(
        "You are a scientific report writer. Return the report as a plain markdown string wrapped in a JSON object: {\"report\": \"...\"}",
        prompt,
    )

    return result.get("report", str(result))
