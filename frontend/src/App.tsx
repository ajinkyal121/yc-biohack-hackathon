import { useState, useCallback } from "react";
import InputPanel from "./components/InputPanel";
import StepIndicator from "./components/StepIndicator";
import StatusStream from "./components/StatusStream";
import ResultPanel from "./components/ResultPanel";
import { startPipeline, streamEvents } from "./api";
import type { PipelineEvent } from "./types";
import "./App.css";

type AppState = "idle" | "running" | "complete" | "error";

function App() {
  const [state, setState] = useState<AppState>("idle");
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [currentStep, setCurrentStep] = useState<number | string>(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [finalReport, setFinalReport] = useState("");

  const handleSubmit = useCallback(async (text: string, files: File[]) => {
    setState("running");
    setEvents([]);
    setCompletedSteps(new Set());
    setCurrentStep(0);
    setFinalReport("");

    try {
      const runId = await startPipeline(text, files);

      streamEvents(
        runId,
        (event) => {
          setEvents((prev) => [...prev, event]);

          if (typeof event.step === "number") {
            if (event.status === "running") {
              setCurrentStep(event.step);
            } else if (event.status === "complete") {
              setCompletedSteps((prev) => new Set([...prev, event.step as number]));
            }
          }

          if (event.step === "final") {
            if (event.status === "done" && event.data) {
              setFinalReport(
                typeof event.data === "string"
                  ? event.data
                  : JSON.stringify(event.data, null, 2)
              );
              setState("complete");
            } else if (event.status === "error") {
              setState("error");
            }
          }
        },
        () => {
          setState("error");
        }
      );
    } catch {
      setState("error");
    }
  }, []);

  return (
    <div className="app">
      <InputPanel onSubmit={handleSubmit} disabled={state === "running"} />

      {state !== "idle" && (
        <>
          <StepIndicator
            currentStep={currentStep}
            completedSteps={completedSteps}
          />
          <StatusStream events={events} />
        </>
      )}

      {state === "complete" && <ResultPanel report={finalReport} />}

      {state === "error" && (
        <div className="error-banner">
          Pipeline encountered an error. Check the logs above for details.
          <button onClick={() => setState("idle")}>Try Again</button>
        </div>
      )}
    </div>
  );
}

export default App;
