import type { PipelineEvent } from "../types";

interface Props {
  events: PipelineEvent[];
}

export default function StatusStream({ events }: Props) {
  if (events.length === 0) return null;

  return (
    <div className="status-stream">
      {events.map((event, i) => (
        <div key={i} className={`event-card ${event.status}`}>
          <div className="event-header">
            <span className="event-step">
              {event.status === "running"
                ? "⏳"
                : event.status === "complete"
                ? "✅"
                : event.status === "error"
                ? "❌"
                : "🏁"}{" "}
              {event.step_name}
            </span>
            <span className="event-status">{event.status}</span>
          </div>
          {event.message && <p className="event-message">{event.message}</p>}
          {event.data && event.status === "complete" && (
            <details>
              <summary>View details</summary>
              <pre className="event-data">
                {JSON.stringify(event.data, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}
