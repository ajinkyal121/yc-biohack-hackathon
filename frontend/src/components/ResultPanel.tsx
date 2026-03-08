import Markdown from "react-markdown";

interface Props {
  report: string;
}

export default function ResultPanel({ report }: Props) {
  if (!report) return null;

  return (
    <div className="result-panel">
      <h2>Final Report</h2>
      <div className="report-content">
        <Markdown>{report}</Markdown>
      </div>
    </div>
  );
}
