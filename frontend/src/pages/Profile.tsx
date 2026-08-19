import { FormEvent, useEffect, useState } from "react";
import ResumeUpload from "../components/ResumeUpload";
import { api, GapAnalysis, Resume, SearchProfile } from "../lib/api";

export default function ProfilePage() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [profile, setProfile] = useState<SearchProfile>({
    country: "in",
    location: "Bangalore",
    locations: [
      { city: "Dubai", country: "ae" },
      { city: "Kochi", country: "in" },
      { city: "Bangalore", country: "in" },
      { city: "Abu Dhabi", country: "ae" },
      { city: "Singapore", country: "sg" },
    ],
    extra_keywords: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [gaps, setGaps] = useState<GapAnalysis | null>(null);
  const [gapsLoading, setGapsLoading] = useState(false);

  useEffect(() => {
    api.getResume().then(setResume).catch(() => setResume(null));
    api.getProfile().then(setProfile);
  }, []);

  const handleUpload = async (file: File) => {
    setMessage("Parsing resume and fetching matched jobs (this can take a few minutes)…");
    setGaps(null);
    try {
      const res = await api.uploadResume(file);
      setResume(res);
      setMessage(
        `Done! Parsed resume, fetched ${res.jobs_fetched ?? 0} jobs and scored ${res.matches_updated ?? 0} matches. Open Jobs or Dashboard to browse.`
      );
    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Upload or job fetch failed. Try again, or use Refresh jobs on the Dashboard."
      );
    }
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const updated = await api.updateProfile(profile);
      setProfile(updated);
      setMessage("Search preferences saved.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleGaps = async () => {
    setGapsLoading(true);
    setMessage("");
    try {
      const result = await api.gapAnalysis();
      setGaps(result);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Gap analysis failed");
    } finally {
      setGapsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Profile</h2>
        <p className="text-slate-500">Upload your resume and configure job search settings</p>
      </div>

      {message && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          {message}
        </div>
      )}

      <section>
        <h3 className="mb-4 text-lg font-semibold">Resume</h3>
        <ResumeUpload onUpload={handleUpload} currentFile={resume?.file_name} />
      </section>

      {resume && (
        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h4 className="font-semibold text-slate-800">Detected titles</h4>
            <ul className="mt-3 space-y-1">
              {resume.titles.length ? (
                resume.titles.map((t) => (
                  <li key={t} className="text-sm text-slate-600">
                    • {t}
                  </li>
                ))
              ) : (
                <li className="text-sm text-slate-400">None detected</li>
              )}
            </ul>
            <p className="mt-4 text-sm text-slate-500">
              Experience: {resume.years_experience > 0 ? `${resume.years_experience} years` : "Not detected — re-upload after update, or add OpenAI key for better parsing"}
            </p>
            {resume.search_query && (
              <p className="mt-2 text-xs text-slate-400">
                Search query: {resume.search_query}
              </p>
            )}
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h4 className="font-semibold text-slate-800">Detected skills</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {resume.skills.length ? (
                resume.skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                  >
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-400">None detected</span>
              )}
            </div>
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Skill gaps</h3>
            <p className="text-sm text-slate-500">
              Compare your resume to your top matched roles
            </p>
          </div>
          <button
            type="button"
            onClick={handleGaps}
            disabled={gapsLoading || !resume}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {gapsLoading ? "Analyzing…" : "Analyze gaps"}
          </button>
        </div>
        {gaps && (
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-600">{gaps.notes}</p>
            <p className="text-xs text-slate-400">Based on {gaps.based_on_jobs} matched jobs</p>
            <div>
              <h4 className="text-sm font-semibold text-slate-800">Missing skills</h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {gaps.missing_skills.length ? (
                  gaps.missing_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800"
                    >
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-400">None flagged</span>
                )}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-800">Suggested next skills</h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {gaps.suggested_skills.length ? (
                  gaps.suggested_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800"
                    >
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-400">None suggested</span>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-4 text-lg font-semibold">Search preferences</h3>
        <form onSubmit={handleSave} className="max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Search cities</label>
            <div className="flex flex-wrap gap-2">
              {profile.locations.map((loc) => (
                <span
                  key={`${loc.city}-${loc.country}`}
                  className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800"
                >
                  {loc.city} ({loc.country.toUpperCase()})
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Jobs are fetched from all cities above on each refresh.
            </p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Extra keywords</label>
            <input
              value={profile.extra_keywords}
              onChange={(e) => setProfile({ ...profile, extra_keywords: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="e.g. fintech, remote"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save preferences"}
          </button>
        </form>
      </section>
    </div>
  );
}
