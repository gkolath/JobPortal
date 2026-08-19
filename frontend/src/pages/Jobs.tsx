import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import JobCard from "../components/JobCard";
import { api, Job, User } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function JobsPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const match = searchParams.get("match") || "relevant";
  const saved = searchParams.get("saved") === "true";
  const applied = searchParams.get("applied") === "true";
  const userId = searchParams.get("user_id") || "";

  const loadJobs = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean | undefined> = {};
      if (match === "relevant" || match === "") {
        // API default: close + good only
      } else if (match === "all") {
        params.include_weak = true;
      } else {
        params.match = match;
        params.include_weak = true;
      }
      if (saved) params.saved = true;
      if (applied) params.applied = true;
      if (userId) params.user_id = parseInt(userId, 10);
      const data = await api.jobs(params);
      setJobs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.users().then(setUsers);
  }, []);

  useEffect(() => {
    loadJobs();
  }, [match, saved, applied, userId]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  const handleUpdate = async (jobId: number, data: { saved?: boolean; applied?: boolean }) => {
    await api.updateJobStatus(jobId, data);
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, ...data } : j))
    );
  };

  const viewingFriend = userId && userId !== String(user?.id);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Job board</h2>
        <p className="text-slate-500">
          {viewingFriend ? "Viewing friend's matches (read-only actions apply to your account)" : "Browse and filter matched jobs"}
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={match || "relevant"}
          onChange={(e) => {
            const v = e.target.value;
            updateFilter("match", v === "relevant" ? "" : v);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="relevant">Relevant only (close + good)</option>
          <option value="close">Close match (≥75%)</option>
          <option value="good">Good match (55–74%)</option>
          <option value="weak">Weak (&lt;55%)</option>
          <option value="all">All scored jobs</option>
        </select>

        <select
          value={userId}
          onChange={(e) => updateFilter("user_id", e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">My matches</option>
          {users
            .filter((u) => u.id !== user?.id)
            .map((u) => (
              <option key={u.id} value={String(u.id)}>
                {u.name}'s matches
              </option>
            ))}
        </select>

        <label className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={saved}
            onChange={(e) => updateFilter("saved", e.target.checked ? "true" : "")}
          />
          Saved only
        </label>

        <label className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={applied}
            onChange={(e) => updateFilter("applied", e.target.checked ? "true" : "")}
          />
          Applied only
        </label>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading jobs…</p>
      ) : jobs.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center">
          <p className="text-slate-600">
            No relevant matches yet. Try Refresh jobs on the Dashboard, or switch the filter to
            “All scored jobs”.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onUpdate={handleUpdate} readOnly={!!viewingFriend} />
          ))}
        </div>
      )}
    </div>
  );
}
