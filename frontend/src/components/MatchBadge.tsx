interface MatchBadgeProps {
  label: "close" | "good" | "weak";
  score: number;
}

const styles = {
  close: "bg-emerald-100 text-emerald-800 border-emerald-200",
  good: "bg-amber-100 text-amber-800 border-amber-200",
  weak: "bg-slate-100 text-slate-600 border-slate-200",
};

const labels = {
  close: "Close match",
  good: "Good match",
  weak: "Weak",
};

export default function MatchBadge({ label, score }: MatchBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[label]}`}
    >
      {labels[label]} · {score}%
    </span>
  );
}
