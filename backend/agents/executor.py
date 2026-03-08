import asyncio
from typing import Callable

from models import ExperimentSpec, ExperimentResult
from services.tamarind import submit_job, poll_job, get_result


async def run_experiments(
    specs: list[ExperimentSpec],
    on_status: Callable[[str], None] | None = None,
) -> list[ExperimentResult]:
    """Step 5: Submit experiments to Tamarind, poll, and collect results.

    Independent jobs run in parallel. Chained jobs (same hypothesis_rank
    with sequential dependencies) run sequentially.
    """
    results = []

    # Group specs by hypothesis_rank
    by_hypothesis: dict[int, list[ExperimentSpec]] = {}
    for spec in specs:
        by_hypothesis.setdefault(spec.hypothesis_rank, []).append(spec)

    async def run_chain(chain: list[ExperimentSpec]) -> list[ExperimentResult]:
        """Run a chain of specs sequentially."""
        chain_results = []
        for spec in chain:
            job_spec = {
                "jobName": spec.job_name,
                "type": spec.type,
                "settings": spec.settings,
            }

            try:
                if on_status:
                    on_status(f"Submitting {spec.job_name} ({spec.type})")

                await submit_job(job_spec)

                await poll_job(
                    spec.job_name,
                    on_status=on_status,
                )

                result_data = await get_result(spec.job_name)

                chain_results.append(ExperimentResult(
                    job_name=spec.job_name,
                    status="completed",
                    results=result_data,
                ))

            except Exception as e:
                chain_results.append(ExperimentResult(
                    job_name=spec.job_name,
                    status="failed",
                    error=str(e),
                ))
                # Stop chain on failure
                break

        return chain_results

    # Run hypothesis chains in parallel
    tasks = [run_chain(chain) for chain in by_hypothesis.values()]
    chain_results = await asyncio.gather(*tasks)

    for chain in chain_results:
        results.extend(chain)

    return results
