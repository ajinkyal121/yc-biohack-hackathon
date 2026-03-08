export interface PipelineEvent {
  step: number | string;
  step_name: string;
  status: "running" | "complete" | "error" | "done";
  data: any;
  message: string;
}

export interface PaperInfo {
  doi: string;
  title: string;
  abstract: string;
  date: string;
  relevance_score: number;
}

export interface Hypothesis {
  rank: number;
  hypothesis: string;
  reasoning: string;
  validation_experiment: string;
  tamarind_tool: string;
  confidence: string;
}

export interface Interpretation {
  hypothesis: string;
  verdict: string;
  confidence: string;
  reasoning: string;
  limitations: string[];
  next_action: string;
}
