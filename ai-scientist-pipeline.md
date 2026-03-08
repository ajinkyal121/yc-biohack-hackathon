# YC Biohack Hackathon
### Hackathon: Tamarind Bio x BioRender @ YC HQ
**Track:** AI Scientist | **Sponsors:** Anthropic · OpenAI · Modal  
**Built by:** Cornucopia Biosciences

---

## Overview

A fully autonomous AI Scientist agent that takes a scientist's research question and executes a closed-loop pipeline — from literature retrieval through in silico simulation — without requiring wet lab execution. The Tamarind Bio API serves as the computational experiment layer.

```
Scientist Input
     ↓
[1] Research Ingestion      ← bioRxiv API + scientist uploads
     ↓
[2] Summarize Findings      ← Claude API
     ↓
[3] Hypothesis Generation   ← Claude API
     ↓
[4] Experiment Design       ← Claude API → Tamarind job spec
     ↓
[5] Experiment Execution    ← Tamarind API (AlphaFold, RFdiffusion, DiffDock)
     ↓
[6] Result Interpretation   ← Claude API
     ↓
Next Iteration (loop back to 3) or Final Report
```

---

## Step 1: Research Ingestion via bioRxiv API

### Goal
Ground the agent in the scientist's specific research context. The bioRxiv API is used for **context enrichment**, not broad discovery — the scientist defines the scope.

### Input — What the Scientist Provides

**Tier 1 — Minimal (plain language statement)**
```
"I am studying whether EGFR mutations in lung cancer affect 
resistance to third-generation tyrosine kinase inhibitors."
```

**Tier 2 — Structured Brief**
```
Research Goal:    Structural basis of osimertinib resistance in EGFR C797S mutants
Target Protein:   EGFR (C797S mutant)
Known Context:    C797S is a tertiary mutation after osimertinib treatment
Key Question:     What alternative binding sites or allosteric pockets exist?
What I Have:      Protein sequence for EGFR C797S variant
What I Don't Know: Whether allosteric inhibitors can overcome resistance
```

**Tier 3 — File Uploads (most powerful)**

| Upload Type | What the Agent Extracts |
|---|---|
| Draft paper / lab notes (PDF) | Prior findings, sequences, methods already tried |
| Experimental data (CSV) | Baseline measurements for simulation comparison |
| Protein sequence (FASTA) | Direct Tamarind input — skips structure guessing |
| Protocol PDF (kit or SOP) | Methods context for experiment design |
| Existing trusted papers (PDF) | Ground truth the agent should align with |

### What the Agent Does

Claude parses the scientist's input and constructs a targeted bioRxiv API query:

```python
# Endpoint: free, no API key required
GET https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/0?category={category}

# Example
GET https://api.biorxiv.org/details/biorxiv/2025-12-08/2026-03-08/0?category=biochemistry
# → filter results by keyword match on title + abstract
# → retrieve top 3–5 PDFs for Claude to read in full
```

**Filtering logic:**
- Relevance scored by Claude against scientist's stated question (0–1)
- Recency weighted — only papers the scientist likely hasn't read
- Deduplication by DOI (API can return multiple versions)
- Flag papers with deposited PDB structures → skip AlphaFold if available

### Output — Research Context Package

```json
{
  "scientist_context": {
    "goal": "Understand structural basis of osimertinib resistance in EGFR C797S",
    "target_protein": "EGFR",
    "mutation": "C797S",
    "provided_sequence": "MRPSGTAGAALLALLAALCPASRA...",
    "known_facts": ["C797S blocks covalent binding of osimertinib"],
    "open_question": "Are there allosteric pockets exploitable by non-covalent inhibitors?"
  },
  "retrieved_papers": [
    {
      "doi": "10.1101/2026.01.22.578901",
      "title": "Cryo-EM structure of EGFR C797S reveals cryptic allosteric pocket",
      "date": "2026-01-22",
      "relevance_score": 0.96,
      "key_finding": "Pocket identified at αC-helix/DFG loop interface",
      "has_pdb_structure": true,
      "pdb_id": "8XYZ",
      "pdf_url": "https://biorxiv.org/content/10.1101/2026.01.22.578901.full.pdf"
    }
  ],
  "synthesis_note": "2 of 5 papers report new structural data on C797S — PDB structures available for direct Tamarind input"
}
```

---

## Step 2: Summarize Findings

### Goal
Extract structured, actionable knowledge from the retrieved papers and the scientist's own context.

### Input
- Research Context Package from Step 1
- Full-text PDFs (top 3–5 papers)
- Scientist-provided documents

### What the Agent Does

Claude reads each paper and extracts structured fields:

```
Prompt pattern:
"Here are {N} recent bioRxiv papers on {topic}, plus the scientist's own notes.
For each paper extract:
  - Target protein and mutation
  - Key experimental finding
  - Method used (cryo-EM, ITC, MD simulation, etc.)
  - Whether a structure was deposited (PDB ID if yes)
  - Open questions or limitations stated by the authors
Return as structured JSON."
```

### Output

```json
[
  {
    "paper_doi": "10.1101/2026.01.22.578901",
    "target": "EGFR C797S",
    "finding": "Cryptic allosteric pocket exists at αC-helix/DFG loop interface",
    "method": "Cryo-EM at 2.8Å resolution",
    "pdb_available": true,
    "pdb_id": "8XYZ",
    "open_questions": [
      "No small molecule validated against this pocket yet",
      "Pocket accessibility under physiological conditions unknown"
    ]
  }
]
```

**Promotion rule:** Only papers with `relevance_score > 0.7` pass to Step 3.

---

## Step 3: Hypothesis Generation

### Goal
Generate specific, testable hypotheses grounded in the summarized findings.

### Input
- Structured summaries from Step 2
- Scientist's open question

### What the Agent Does

```
Prompt pattern:
"Given these findings about {target}, and the scientist's open question: '{question}',
generate 3 ranked hypotheses. For each:
  - State the hypothesis clearly
  - Explain the mechanistic reasoning
  - Specify what computational experiment would validate or refute it
  - Map to a specific Tamarind tool (AlphaFold / RFdiffusion / DiffDock / ProteinMPNN)
Return as structured JSON, ranked by confidence."
```

### Output

```json
[
  {
    "rank": 1,
    "hypothesis": "Small molecules targeting the αC-helix/DFG allosteric pocket of EGFR C797S can inhibit kinase activity without requiring covalent binding",
    "reasoning": "Cryo-EM data confirms pocket exists; no covalent bond required means C797S mutation is irrelevant",
    "validation_experiment": "Virtual screen known allosteric inhibitor scaffolds against PDB 8XYZ using DiffDock",
    "tamarind_tool": "diffdock",
    "confidence": "high"
  },
  {
    "rank": 2,
    "hypothesis": "ProteinMPNN-redesigned sequences around C797 will recover osimertinib binding via alternative contacts",
    "reasoning": "Sequence redesign may restore non-covalent contacts disrupted by C797S",
    "validation_experiment": "Design 10 sequence variants around active site, predict structure with AlphaFold, dock osimertinib",
    "tamarind_tool": "proteinmpnn → alphafold → diffdock",
    "confidence": "medium"
  }
]
```

---

## Step 4: Experiment Design

### Goal
Translate each hypothesis into a concrete, executable Tamarind API job specification.

### Input
- Ranked hypotheses from Step 3
- PDB IDs or FASTA sequences from Step 1

### What the Agent Does

Claude auto-generates Tamarind API payloads for each hypothesis:

**Example — DiffDock (molecular docking)**
```python
params = {
  "jobName": "hypothesis_1_diffdock_egfr_c797s",
  "type": "diffdock",
  "settings": {
    "protein": "8XYZ",          # PDB ID from paper
    "ligand": "<sdf_content>",  # known allosteric scaffold
    "num_poses": 10
  }
}
```

**Example — AlphaFold (structure prediction)**
```python
params = {
  "jobName": "hypothesis_2_alphafold_egfr_variant",
  "type": "alphafold",
  "settings": {
    "sequence": "MRPSGTAGAA...",   # scientist-provided or redesigned
    "numModels": 5,
    "numRecycles": 3
  }
}
```

**Example — Chained pipeline (ProteinMPNN → AlphaFold → DiffDock)**
```python
# Submit via /run-pipeline for saved multi-step pipelines
POST https://app.tamarind.bio/api/run-pipeline
```

### Output
A job manifest — list of Tamarind job specs ready for execution, linked to their parent hypothesis.

---

## Step 5: Experiment Execution (Tamarind API)

### Goal
Run in silico simulations as proxies for wet lab experiments.

### Tamarind Tools Available

| Tool | Use Case |
|---|---|
| **AlphaFold** | Protein structure prediction from sequence |
| **RFdiffusion** | De novo protein backbone design |
| **ProteinMPNN** | Sequence design for a given backbone |
| **DiffDock** | Blind molecular docking (protein + ligand) |
| **RoseTTAFold All Atom** | Structure prediction for protein + small molecule complexes |
| **AlphaFlow** | Protein conformational ensemble / dynamics |

### API Pattern

```python
import requests, time

base_url = "https://app.tamarind.bio/api/"
headers = {"x-api-key": TAMARIND_API_KEY}

# 1. Submit job
response = requests.post(base_url + "submit-job", headers=headers, json=params)
job_name = params["jobName"]

# 2. Poll for completion
while True:
    status = requests.get(base_url + "jobs", headers=headers, 
                          params={"jobName": job_name}).json()
    if status["status"] == "completed":
        break
    time.sleep(30)

# 3. Download results
result = requests.post(base_url + "result", headers=headers, 
                       json={"jobName": job_name})
```

### Output — Raw Simulation Results

```json
{
  "job_name": "hypothesis_1_diffdock_egfr_c797s",
  "status": "completed",
  "results": {
    "top_pose_confidence": 0.84,
    "docking_score": -9.2,
    "rmsd_to_known_inhibitor": 1.3,
    "pose_pdb_url": "https://app.tamarind.bio/results/hypothesis_1/pose_1.pdb"
  }
}
```

---

## Step 6: Result Interpretation + Loop

### Goal
Have Claude interpret simulation results in the context of the original hypothesis, then decide: report findings or propose next experiment.

### Input
- Raw Tamarind results from Step 5
- Original hypothesis
- Scientist's open question

### What the Agent Does

```
Prompt pattern:
"Hypothesis: '{hypothesis}'
Simulation results: {results}
Interpret these results:
  - Does this support or refute the hypothesis?
  - What is the confidence level and why?
  - What are the limitations of this in silico result?
  - Should we run another experiment? If yes, what?
Return interpretation + recommended next action."
```

### Output — Interpretation Report

```json
{
  "hypothesis": "Small molecules targeting αC-helix/DFG pocket can inhibit EGFR C797S",
  "verdict": "SUPPORTED",
  "confidence": "medium-high",
  "reasoning": "Top docking pose achieves -9.2 kcal/mol binding energy at allosteric site with RMSD 1.3Å from known inhibitor scaffold — comparable to approved allosteric binders",
  "limitations": [
    "DiffDock does not account for induced fit / protein flexibility",
    "Binding energy is estimated, not experimental Kd"
  ],
  "next_action": "run_alphafold_with_ligand",
  "next_experiment": {
    "tool": "rosettafold_all_atom",
    "rationale": "Confirm pocket geometry with ligand present using RoseTTAFold All Atom"
  }
}
```

If `next_action = "run_alphafold_with_ligand"` → loop back to Step 4.  
If `next_action = "report"` → generate final summary for scientist.

---

## Tech Stack

| Component | Tool | Notes |
|---|---|---|
| Paper retrieval | `api.biorxiv.org` | Free, no API key, paginated JSON |
| PDF reading | Claude API (native PDF support) | Pass as base64 |
| All reasoning steps | Claude API `claude-sonnet-4-20250514` | Uses $5k hackathon credits |
| Structure prediction | Tamarind AlphaFold | Uses hackathon API keys |
| Protein design | Tamarind RFdiffusion / ProteinMPNN | |
| Molecular docking | Tamarind DiffDock | |
| Orchestration | Python async + polling loop | |
| UI | React (single text box + file upload) | |

---

## Hackathon Demo Flow (Suggested)

1. Scientist types: *"I'm studying EGFR C797S resistance to osimertinib. Can allosteric inhibition overcome this?"*
2. Agent retrieves 5 recent bioRxiv papers → finds PDB 8XYZ
3. Claude summarizes: cryptic pocket confirmed by cryo-EM
4. Claude generates hypothesis: allosteric docking without covalent bond
5. Tamarind DiffDock runs against PDB 8XYZ + known scaffold
6. Claude interprets: docking score -9.2 → SUPPORTED → recommends RoseTTAFold follow-up
7. Show full loop live

**Total estimated runtime for demo:** ~5–10 minutes per loop iteration

---

## Known Limitations & Open Questions

| Issue | Impact | Mitigation |
|---|---|---|
| bioRxiv API has no native keyword search | May miss relevant papers | Use Claude to score abstracts post-retrieval |
| PDF scraping rate limits on bioRxiv | Can't fetch all full texts | Limit to top 3–5 PDFs; use abstracts for others |
| Tamarind job latency (AlphaFold ~10–30 min) | Slows live demo | Pre-run jobs or use faster tools (DiffDock ~2 min) for demo |
| In silico results ≠ experimental validation | Scientific caveat | Clearly label all results as computational predictions |
| No real-time Tamarind webhook | Must poll for completion | Implement async polling with status UI |

---

## References

- [Tamarind Bio API Docs](https://app.tamarind.bio/api-docs/nampnn)
- [Tamarind Bio — YC Company Page](https://www.ycombinator.com/companies/tamarind-bio)
- [bioRxiv REST API](https://api.biorxiv.org/)
- [Tamarind Bio Features](https://www.tamarind.bio/features)
