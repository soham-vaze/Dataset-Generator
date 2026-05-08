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
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex justify-between items-center px-6 py-3 bg-dark-100/60 backdrop-blur-xl border-b border-white/[0.04] z-20"
    >
      <div className="flex items-center gap-4">
        {/* Quick stats */}
        <div className="hidden md:flex items-center gap-3">
          {pendingCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="text-[11px] font-medium text-primary-300">
                {pendingCount} generating
              </span>
            </div>
          )}
          {completedCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[11px] font-medium text-emerald-400">
                {completedCount} completed
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* User email */}
        {userEmail && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary/60 to-blue-500/60 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white uppercase">
                {userEmail.charAt(0)}
              </span>
            </div>
            <span className="text-xs text-zinc-400 font-medium hidden sm:block max-w-[160px] truncate">
              {userEmail}
            </span>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={logout}
          className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-zinc-400 bg-white/[0.03] border border-white/[0.06] hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-400 transition-all duration-200"
        >
          Logout
        </button>
      </div>
    </motion.div>
  );
}

export default Header;
