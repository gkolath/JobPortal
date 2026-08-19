import MatchBadge from "./MatchBadge";
import { Job } from "../lib/api";

interface JobCardProps {
  job: Job;
  onUpdate: (jobId: number, data: { saved?: boolean; applied?: boolean }) => void;
  readOnly?: boolean;
}

export default function JobCard({ job, onUpdate, readOnly = false }: JobCardProps) {
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
          </>
        )}
      </div>
    </article>
  );
}
