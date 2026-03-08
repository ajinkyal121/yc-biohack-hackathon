const STEPS = [
  { num: 1, label: "Ingest" },
  { num: 2, label: "Summarize" },
  { num: 3, label: "Hypothesize" },
  { num: 4, label: "Design" },
  { num: 5, label: "Execute" },
  { num: 6, label: "Interpret" },
];

interface Props {
  currentStep: number | string;
  completedSteps: Set<number>;
}

export default function StepIndicator({ currentStep, completedSteps }: Props) {
  return (
    <div className="step-indicator">
      {STEPS.map(({ num, label }) => {
        let className = "step-dot";
        if (completedSteps.has(num)) className += " completed";
        else if (currentStep === num) className += " active";

        return (
          <div key={num} className={className}>
            <div className="dot">{completedSteps.has(num) ? "✓" : num}</div>
            <span className="step-label">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
