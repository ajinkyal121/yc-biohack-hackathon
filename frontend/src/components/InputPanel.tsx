import { useState, useRef, DragEvent } from "react";

interface Props {
  onSubmit: (text: string, files: File[]) => void;
  disabled: boolean;
}

export default function InputPanel({ onSubmit, disabled }: Props) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  };

  const handleSubmit = () => {
    if (!text.trim()) return;
    onSubmit(text, files);
  };

  return (
    <div className="input-panel">
      <h2>YC Biohack Hackathon</h2>
      <p className="subtitle">
        Describe your research question and optionally upload supporting files
        (PDFs, FASTA, CSV).
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g., I'm studying EGFR C797S resistance to osimertinib. Can allosteric inhibition overcome this?"
        rows={5}
        disabled={disabled}
      />

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.csv,.fasta,.fa,.txt"
          style={{ display: "none" }}
          onChange={(e) => {
            const selected = Array.from(e.target.files || []);
            setFiles((prev) => [...prev, ...selected]);
          }}
        />
        {files.length === 0
          ? "Drop files here or click to browse"
          : files.map((f) => f.name).join(", ")}
      </div>

      <button onClick={handleSubmit} disabled={disabled || !text.trim()}>
        {disabled ? "Running..." : "Start Pipeline"}
      </button>
    </div>
  );
}
