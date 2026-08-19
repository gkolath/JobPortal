import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, DashboardStats, Job } from "../lib/api";
import JobCard from "../components/JobCard";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [topJobs, setTopJobs] = useState<Job[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");

  const load = async () => {
    const [dashboard, jobs] = await Promise.all([
      api.dashboard(),
      api.jobs({}),
    ]);
    setStats(dashboard);
    setTopJobs(jobs.slice(0, 5));
  };

  useEffect(() => {
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    setMessage("");
    try {
      const res = await api.refreshJobs();
      setMessage(`Fetched ${res.jobs_fetched} jobs, updated ${res.matches_updated} matches.`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  if (!stats) {
    return <div className="text-slate-500">Loading dashboard…</div>;
  }

  const cards = [
    { label: "Close matches", sub: "≥75% fit", value: stats.close_matches, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Good matches", sub: "55–74% fit", value: stats.good_matches, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "All jobs", sub: "scored for you", value: stats.total_jobs, color: "text-brand-600", bg: "bg-brand-50" },
    { label: "Saved", sub: "bookmarked", value: stats.saved_count, color: "text-sky-600", bg: "bg-sky-50" },
    { label: "Applied", sub: "marked applied", value: stats.applied_count, color: "text-violet-600", bg: "bg-violet-50" },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-slate-500">
            {stats.total_jobs} jobs scored against your resume
            {stats.weak_matches > 0 && stats.close_matches === 0 && stats.good_matches === 0
              ? " — browse all jobs on the Jobs tab"
              : ""}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-50"
        >
          {refreshing ? "Refreshing jobs…" : "Refresh jobs"}
        </button>
      </div>

      {message && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          {message}
        </div>
      )}

      {!stats.has_resume && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
          <p className="font-medium text-amber-900">Upload your resume first</p>
          <p className="mt-1 text-sm text-amber-700">
            We need your resume to score jobs against your skills.{" "}
            <Link to="/profile" className="font-semibold underline">
              Go to Profile
            </Link>
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-xl border border-slate-200 ${c.bg} p-5`}>
            <p className="text-sm font-medium text-slate-600">{c.label}</p>
            <p className="text-xs text-slate-400">{c.sub}</p>
            <p className={`mt-2 text-3xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          to="/jobs"
          className="rounded-xl border-2 border-brand-300 bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h3 className="font-semibold text-brand-800">View all jobs ({stats.total_jobs})</h3>
          <p className="mt-1 text-sm text-slate-500">Browse every job scored for your profile</p>
        </Link>
        <Link
          to="/jobs?match=close"
          className="rounded-xl border border-emerald-200 bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h3 className="font-semibold text-emerald-800">Close matches ({stats.close_matches})</h3>
          <p className="mt-1 text-sm text-slate-500">Jobs scoring 75% or higher</p>
        </Link>
        <Link
          to="/jobs?match=good"
          className="rounded-xl border border-amber-200 bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h3 className="font-semibold text-amber-800">Good matches ({stats.good_matches})</h3>
          <p className="mt-1 text-sm text-slate-500">Jobs scoring 55–74%</p>
        </Link>
      </div>

      {topJobs.length > 0 && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900">Top matches for you</h3>
            <Link to="/jobs" className="text-sm font-medium text-brand-600 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-4">
            {topJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onUpdate={async (jobId, data) => {
                  await api.updateJobStatus(jobId, data);
                  await load();
                }}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
