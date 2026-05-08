import { motion, AnimatePresence } from "framer-motion";
import { usePendingJobs } from "../context/PendingJobsContext";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import GlassCard from "../components/GlassCard";

const STATUS_CONFIG = {
  pending: {
    label: "In Progress",
    icon: <Loader2 size={18} className="animate-spin text-primary-400" />,
    badge: "bg-primary/10 text-primary-300 border border-primary/20",
    glow: "border-primary/10",
  },
  done: {
    label: "Completed",
    icon: <CheckCircle2 size={18} className="text-emerald-400" />,
    badge: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    glow: "border-emerald-500/10",
  },
  failed: {
    label: "Failed",
    icon: <XCircle size={18} className="text-red-400" />,
    badge: "bg-red-500/10 text-red-400 border border-red-500/20",
    glow: "border-red-500/10",
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
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-4">
            <Clock size={28} className="text-zinc-600" />
          </div>
          <p className="text-lg font-medium text-zinc-400">No jobs yet</p>
          <p className="text-sm text-zinc-600 mt-2">
            Submitted generation requests will appear here.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h2 className="text-2xl font-bold text-zinc-100 tracking-tight mb-2">
          Generation Pipeline
        </h2>
        <p className="text-zinc-500 text-sm">
          Track your dataset generation requests in real-time
        </p>
      </motion.div>

      {pending.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <h3 className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">
              In Progress ({pending.length})
            </h3>
          </div>
          <div className="space-y-3">
            <AnimatePresence>
              {pending.map((job, i) => (
                <JobCard key={job.id} job={job} index={i} />
              ))}
            </AnimatePresence>
          </div>
        </section>
      )}

      {rest.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500 mb-4">
            Completed / Failed
          </h3>
          <div className="space-y-3">
            {rest.map((job, i) => (
              <JobCard key={job.id} job={job} index={i} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function JobCard({ job, index = 0 }) {
  const cfg = STATUS_CONFIG[job.status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ delay: index * 0.05 }}
      className={`
        rounded-2xl border bg-white/[0.02] p-5
        transition-all duration-300
        ${cfg.glow}
        hover:bg-white/[0.04]
      `}
    >
      <div className="flex items-start gap-4">
        <div className="mt-0.5">{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-zinc-200 text-sm truncate">{job.name}</span>
            <span className={`text-[10px] px-2.5 py-1 rounded-full font-medium whitespace-nowrap ${cfg.badge}`}>
              {cfg.label}
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-2 flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded-md bg-white/[0.04] text-zinc-400 font-medium">
              {job.type?.toUpperCase()}
            </span>
            <span>Started: {new Date(job.startedAt).toLocaleTimeString()}</span>
            <span>·</span>
            <span>
              {job.status === "pending"
                ? `Running for ${elapsed(job.startedAt, null)}`
                : `Took ${elapsed(job.startedAt, job.finishedAt)}`}
            </span>
          </p>
          {job.status === "failed" && job.error && (
            <p className="text-[11px] text-red-400 mt-2 bg-red-500/5 px-3 py-1.5 rounded-lg">
              Error: {job.error}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
