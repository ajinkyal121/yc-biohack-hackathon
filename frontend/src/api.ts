import type { PipelineEvent } from "./types";

export async function startPipeline(
  text: string,
  files: File[]
): Promise<string> {
  const formData = new FormData();
  formData.append("text", text);
  files.forEach((f) => formData.append("files", f));

  const res = await fetch("/api/run", { method: "POST", body: formData });
  const { run_id } = await res.json();
  return run_id;
}

export function streamEvents(
  runId: string,
  onEvent: (e: PipelineEvent) => void,
  onError?: (err: Event) => void
): EventSource {
  const es = new EventSource(`/api/stream/${runId}`);
  es.onmessage = (msg) => {
    const event: PipelineEvent = JSON.parse(msg.data);
    onEvent(event);
    if (event.status === "done" || (event.status === "error" && event.step === "final")) {
      es.close();
    }
  };
  es.onerror = (err) => {
    onError?.(err);
    es.close();
  };
  return es;
}
