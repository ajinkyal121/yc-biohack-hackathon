from __future__ import annotations
from pydantic import BaseModel
from typing import Any


class ScientistInput(BaseModel):
    text: str
    files: list[dict] = []  # [{"filename": str, "content_base64": str, "media_type": str}]


class PaperInfo(BaseModel):
    doi: str
    title: str
    abstract: str
    date: str
    relevance_score: float = 0.0
    has_pdb_structure: bool = False
    pdb_id: str | None = None
    pdf_base64: str | None = None


class ResearchContext(BaseModel):
    goal: str = ""
    target_protein: str = ""
    mutation: str = ""
    provided_sequence: str = ""
    known_facts: list[str] = []
    open_question: str = ""
    search_keywords: list[str] = []
    biorxiv_category: str = "biochemistry"
    papers: list[PaperInfo] = []
    previous_results: list[dict] = []


class PaperSummary(BaseModel):
    paper_doi: str
    target: str
    finding: str
    method: str
    pdb_available: bool = False
    pdb_id: str | None = None
    open_questions: list[str] = []


class Hypothesis(BaseModel):
    rank: int
    hypothesis: str
    reasoning: str
    validation_experiment: str
    tamarind_tool: str
    confidence: str


class ExperimentSpec(BaseModel):
    job_name: str
    type: str  # alphafold, diffdock, proteinmpnn, rfdiffusion, rosettafold
    settings: dict[str, Any]
    hypothesis_rank: int = 0


class ExperimentResult(BaseModel):
    job_name: str
    status: str
    results: dict[str, Any] = {}
    error: str | None = None


class Interpretation(BaseModel):
    hypothesis: str
    verdict: str  # SUPPORTED, REFUTED, INCONCLUSIVE
    confidence: str
    reasoning: str
    limitations: list[str] = []
    next_action: str  # "report" or "run_next_experiment"
    next_experiment: dict[str, Any] | None = None


class PipelineEvent(BaseModel):
    step: int | str
    step_name: str
    status: str  # running, complete, error
    data: Any = None
    message: str = ""
