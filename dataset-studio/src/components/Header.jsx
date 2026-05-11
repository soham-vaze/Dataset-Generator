import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { usePendingJobs } from "../context/PendingJobsContext";

function Header() {
  const { logout, userEmail } = useAuth();
  const { myJobs } = usePendingJobs();
  const pendingCount = myJobs.filter((j) => j.status === "pending").length;
  const completedCount = myJobs.filter((j) => j.status === "done").length;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="flex justify-between items-center px-6 h-14 bg-dark-50/60 backdrop-blur-2xl border-b border-white/[0.035] z-20"
    >
      {/* Left: status pills */}
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2.5">
          {pendingCount > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/[0.08] border border-primary/[0.15]"
            >
              <div className="relative">
                <div className="w-1.5 h-1.5 rounded-full bg-primary-400" />
                <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-primary-400 animate-ping opacity-40" />
              </div>
              <span className="text-[11px] font-semibold text-primary-300 tracking-wide">
                {pendingCount} generating
              </span>
            </motion.div>
          )}
          {completedCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/[0.08] border border-emerald-500/[0.15]">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[11px] font-semibold text-emerald-400 tracking-wide">
                {completedCount} completed
              </span>
            </div>
          )}
          {pendingCount === 0 && completedCount === 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.04]">
              <div className="w-1.5 h-1.5 rounded-full bg-zinc-600" />
              <span className="text-[11px] font-medium text-zinc-600 tracking-wide">
                Ready
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Right: user + logout */}
      <div className="flex items-center gap-2.5">
        {userEmail && (
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-white/[0.025] border border-white/[0.05] hover:bg-white/[0.04] transition-colors duration-200">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-primary-500/70 to-blue-500/70 flex items-center justify-center ring-1 ring-white/[0.08]">
              <span className="text-[10px] font-bold text-white uppercase">
                {userEmail.charAt(0)}
              </span>
            </div>
            <span className="text-[12px] text-zinc-400 font-medium hidden sm:block max-w-[160px] truncate">
              {userEmail}
            </span>
          </div>
        )}

        <button
          onClick={logout}
          className="group px-3.5 py-1.5 rounded-xl text-[12px] font-medium text-zinc-500 bg-white/[0.025] border border-white/[0.05] hover:bg-red-500/[0.08] hover:border-red-500/[0.15] hover:text-red-400 transition-all duration-300 flex items-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
          </svg>
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </motion.div>
  );
}

export default Header;
