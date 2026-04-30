import { usePendingJobs } from "../context/PendingJobsContext";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

const STATUS_CONFIG = {
  pending: {
    label: "In Progress",
    icon: <Loader2 size={18} className="animate-spin text-indigo-500" />,
    badge: "bg-indigo-50 text-indigo-600 border border-indigo-200",
  },
  done: {
    label: "Completed",
    icon: <CheckCircle2 size={18} className="text-green-500" />,
    badge: "bg-green-50 text-green-600 border border-green-200",
  },
  failed: {
    label: "Failed",
    icon: <XCircle size={18} className="text-red-500" />,
    badge: "bg-red-50 text-red-600 border border-red-200",
  },
};

function elapsed(startedAt, finishedAt) {
  const end = finishedAt ? new Date(finishedAt) : new Date();
  const secs = Math.round((end - new Date(startedAt)) / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

export default function Pipeline() {
  const { myJobs } = usePendingJobs();

  const pending = myJobs.filter((j) => j.status === "pending");
  const rest = myJobs.filter((j) => j.status !== "pending");

  if (myJobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-zinc-400">
        <Clock size={48} className="mb-4 opacity-40" />
        <p className="text-lg font-medium">No jobs yet</p>
        <p className="text-sm mt-1">Submitted generation requests will appear here.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold text-zinc-900 mb-6">Generation Pipeline</h2>

      {pending.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 mb-3">
            In Progress ({pending.length})
          </h3>
          <div className="space-y-3">
            {pending.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </section>
      )}

      {rest.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 mb-3">
            Completed / Failed
          </h3>
          <div className="space-y-3">
            {rest.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function JobCard({ job }) {
  const cfg = STATUS_CONFIG[job.status];

  return (
    <div className="bg-white rounded-2xl border border-zinc-100 shadow-sm p-4 flex items-start gap-4">
      <div className="mt-0.5">{cfg.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-zinc-800 truncate">{job.name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${cfg.badge}`}>
            {cfg.label}
          </span>
        </div>
        <p className="text-xs text-zinc-400 mt-1">
          Type: <span className="font-medium text-zinc-500">{job.type?.toUpperCase()}</span>
          {" · "}
          Started: {new Date(job.startedAt).toLocaleTimeString()}
          {" · "}
          {job.status === "pending"
            ? `Running for ${elapsed(job.startedAt, null)}`
            : `Took ${elapsed(job.startedAt, job.finishedAt)}`}
        </p>
        {job.status === "failed" && job.error && (
          <p className="text-xs text-red-500 mt-1">Error: {job.error}</p>
        )}
      </div>
    </div>
  );
}
