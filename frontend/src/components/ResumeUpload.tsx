import { useRef, useState } from "react";

interface UploadProps {
  onUpload: (file: File) => Promise<void>;
  currentFile?: string;
}

export default function ResumeUpload({ onUpload, currentFile }: UploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = async (file: File) => {
    setError("");
    setUploading(true);
    try {
      await onUpload(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-100 text-2xl">
        📄
      </div>
      <p className="font-medium text-slate-800">Upload your resume</p>
      <p className="mt-1 text-sm text-slate-500">PDF or DOCX, up to 10 MB</p>
      {currentFile && (
        <p className="mt-2 text-sm text-brand-700">Current: {currentFile}</p>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="mt-4 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {uploading ? "Uploading…" : "Choose file"}
      </button>
    </div>
  );
}
