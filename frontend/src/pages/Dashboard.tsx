import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, DashboardStats } from "../lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => api.dashboard().then(setStats);

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
    { label: "Close matches", value: stats.close_matches, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Good matches", value: stats.good_matches, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Total scored", value: stats.total_jobs, color: "text-brand-600", bg: "bg-brand-50" },
    { label: "Saved", value: stats.saved_count, color: "text-sky-600", bg: "bg-sky-50" },
    { label: "Applied", value: stats.applied_count, color: "text-violet-600", bg: "bg-violet-50" },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-slate-500">Your job match overview</p>
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
            <p className={`mt-2 text-3xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/jobs?match=close"
          className="rounded-xl border border-emerald-200 bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h3 className="font-semibold text-emerald-800">View close matches</h3>
          <p className="mt-1 text-sm text-slate-500">Jobs scoring 75% or higher for you</p>
        </Link>
        <Link
          to="/jobs?saved=true"
          className="rounded-xl border border-sky-200 bg-white p-6 shadow-sm transition hover:shadow-md"
        >
          <h3 className="font-semibold text-sky-800">View saved jobs</h3>
          <p className="mt-1 text-sm text-slate-500">Jobs you've bookmarked</p>
        </Link>
      </div>
    </div>
  );
}
