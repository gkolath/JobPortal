import { useState } from "react";
import MatchBadge from "./MatchBadge";
import { api, Job } from "../lib/api";

interface JobCardProps {
  job: Job;
  onUpdate: (jobId: number, data: { saved?: boolean; applied?: boolean }) => void;
  readOnly?: boolean;
}

export default function JobCard({ job, onUpdate, readOnly = false }: JobCardProps) {
  const [coverOpen, setCoverOpen] = useState(false);
  const [coverText, setCoverText] = useState("");
  const [coverLoading, setCoverLoading] = useState(false);
  const [coverError, setCoverError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleCoverLetter = async (force = false) => {
    setCoverOpen(true);
    setCoverError("");
    setCopied(false);
    if (coverText && !force) return;
    setCoverLoading(true);
    setCoverText("");
    try {
      const res = await api.coverLetter(job.id);
      setCoverText(res.text);
    } catch (e) {
      setCoverError(e instanceof Error ? e.message : "Failed to draft cover letter");
    } finally {
      setCoverLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!coverText) return;
    await navigator.clipboard.writeText(coverText);
    setCopied(true);
  };

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <MatchBadge label={job.label} score={job.score} />
            {job.saved && (
              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
                Saved
              </span>
            )}
            {job.applied && (
              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">
                Applied
              </span>
            )}
          </div>
          <h3 className="text-lg font-semibold text-slate-900">{job.title}</h3>
          <p className="mt-1 text-sm text-slate-600">
            {job.company || "Unknown company"} · {job.location || "Remote"}
          </p>
        </div>
        <span className="text-xs uppercase tracking-wide text-slate-400">{job.source}</span>
      </div>

      <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-slate-600">
        {job.description}
      </p>

      {job.fit_reason && (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <span className="font-medium text-slate-800">Why this match: </span>
          {job.fit_reason}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Open posting
          </a>
        )}
        {!readOnly && (
          <>
            <button
              onClick={() => onUpdate(job.id, { saved: !job.saved })}
              className={`rounded-lg border px-4 py-2 text-sm font-medium ${
                job.saved
                  ? "border-sky-300 bg-sky-50 text-sky-700"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {job.saved ? "Unsave" : "Save"}
            </button>
            <button
              onClick={() => onUpdate(job.id, { applied: !job.applied })}
              className={`rounded-lg border px-4 py-2 text-sm font-medium ${
                job.applied
                  ? "border-violet-300 bg-violet-50 text-violet-700"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {job.applied ? "Mark not applied" : "Applied"}
            </button>
            <button
              onClick={() => handleCoverLetter()}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Draft cover letter
            </button>
          </>
        )}
      </div>

      {coverOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h4 className="text-lg font-semibold text-slate-900">Cover letter draft</h4>
              <button
                onClick={() => setCoverOpen(false)}
                className="text-sm text-slate-500 hover:text-slate-800"
              >
                Close
              </button>
            </div>
            <p className="mb-3 text-xs text-slate-500">
              {job.title} · {job.company || "Company"}
            </p>
            {coverLoading && <p className="text-sm text-slate-500">Generating…</p>}
            {coverError && <p className="text-sm text-red-600">{coverError}</p>}
            {coverText && (
              <>
                <textarea
                  readOnly
                  value={coverText}
                  rows={14}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800"
                />
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={handleCopy}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                  >
                    {copied ? "Copied" : "Copy"}
                  </button>
                  <button
                    onClick={() => handleCoverLetter(true)}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Regenerate
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
