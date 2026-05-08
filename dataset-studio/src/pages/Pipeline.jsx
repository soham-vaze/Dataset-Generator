import { motion, AnimatePresence } from "framer-motion";
import { usePendingJobs } from "../context/PendingJobsContext";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

const STATUS_CONFIG = {
  pending: {
    label: "In Progress",
    icon: <Loader2 size={18} className="animate-spin text-primary-400" />,
    badge: "bg-primary/[0.08] text-primary-300 border border-primary/[0.15]",
    glow: "border-primary/[0.1]",
    accent: "bg-primary/[0.03]",
  },
  done: {
    label: "Completed",
    icon: <CheckCircle2 size={18} className="text-emerald-400" />,
    badge: "bg-emerald-500/[0.08] text-emerald-400 border border-emerald-500/[0.15]",
    glow: "border-emerald-500/[0.1]",
    accent: "bg-emerald-500/[0.02]",
  },
  failed: {
    label: "Failed",
    icon: <XCircle size={18} className="text-red-400" />,
    badge: "bg-red-500/[0.08] text-red-400 border border-red-500/[0.15]",
    glow: "border-red-500/[0.1]",
    accent: "bg-red-500/[0.02]",
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
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ease: [0.25, 0.46, 0.45, 0.94] }}
          className="text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-center mx-auto mb-5">
            <Clock size={28} className="text-zinc-700" />
          </div>
          <p className="text-[17px] font-semibold text-zinc-400 tracking-tight">No jobs yet</p>
          <p className="text-sm text-zinc-600 mt-2 max-w-xs mx-auto">
            Submitted generation requests will appear here in real-time.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ease: [0.25, 0.46, 0.45, 0.94] }}
        className="mb-8"
      >
        <h2 className="text-2xl font-bold text-zinc-100 tracking-[-0.02em] mb-2">
          Generation Pipeline
        </h2>
        <p className="text-zinc-500 text-sm">
          Track your dataset generation requests in real-time
        </p>
      </motion.div>

      {pending.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-primary-400" />
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-primary-400 animate-ping opacity-40" />
            </div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-500">
              In Progress ({pending.length})
            </h3>
          </div>
          <div className="space-y-2.5">
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
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-500 mb-4">
            Completed / Failed ({rest.length})
          </h3>
          <div className="space-y-2.5">
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
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -12, transition: { duration: 0.2 } }}
      transition={{ delay: index * 0.04, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`
        relative rounded-2xl border p-5 overflow-hidden
        transition-all duration-300
        ${cfg.glow} ${cfg.accent}
        hover:bg-white/[0.03]
      `}
    >
      {/* Side accent */}
      {job.status === "pending" && (
        <div className="absolute left-0 top-3 bottom-3 w-[2px] rounded-r-full bg-gradient-to-b from-primary-400 to-primary-600" />
      )}

      <div className="flex items-start gap-4">
        <div className="mt-0.5 shrink-0">{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3">
            <span className="font-medium text-zinc-200 text-sm truncate">{job.name}</span>
            <span className={`text-[10px] px-2.5 py-1 rounded-full font-semibold whitespace-nowrap ${cfg.badge}`}>
              {cfg.label}
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-2.5 flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded-md bg-white/[0.04] text-zinc-400 font-semibold text-[10px] uppercase tracking-wider">
              {job.type?.toUpperCase()}
            </span>
            <span className="text-zinc-600">·</span>
            <span>Started {new Date(job.startedAt).toLocaleTimeString()}</span>
            <span className="text-zinc-600">·</span>
            <span className={job.status === "pending" ? "text-primary-300" : ""}>
              {job.status === "pending"
                ? `Running for ${elapsed(job.startedAt, null)}`
                : `Took ${elapsed(job.startedAt, job.finishedAt)}`}
            </span>
          </p>
          {job.status === "failed" && job.error && (
            <p className="text-[11px] text-red-400 mt-3 bg-red-500/[0.05] border border-red-500/[0.1] px-3 py-2 rounded-xl">
              {job.error}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
