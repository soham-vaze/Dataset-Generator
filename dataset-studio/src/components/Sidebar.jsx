import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { datasetConfigs } from "../config/datasetConfigs";
import { usePendingJobs } from "../context/PendingJobsContext";
import { categoryMeta } from "./CategoryCard";

export default function Sidebar({ onSelectDataset }) {
  const navigate = useNavigate();
  const { myJobs } = usePendingJobs();
  const pendingCount = myJobs.filter((j) => j.status === "pending").length;
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredKey, setHoveredKey] = useState(null);

  const handleDatasetClick = (key) => {
    onSelectDataset(key);
    navigate("/");
  };

  return (
    <motion.div
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="relative flex flex-col h-full bg-dark-100/80 backdrop-blur-xl border-r border-white/[0.04] z-30"
    >
      {/* Logo area */}
      <div className="px-4 pt-5 pb-4 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center flex-shrink-0 shadow-glow">
          <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" opacity="0.5" />
            <path d="M2 12l10 5 10-5" opacity="0.7" />
          </svg>
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <h2 className="text-sm font-bold text-zinc-100 tracking-tight">Dataset Studio</h2>
              <p className="text-[10px] text-zinc-500 font-medium">AI Dataset Generator</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-7 w-6 h-6 rounded-full bg-dark-200 border border-white/[0.08] flex items-center justify-center hover:bg-dark-300 transition-colors z-50"
      >
        <svg
          className={`w-3 h-3 text-zinc-400 transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Divider */}
      <div className="mx-4 h-px bg-white/[0.04]" />

      {/* Section label */}
      <AnimatePresence>
        {!collapsed && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-5 pt-5 pb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500"
          >
            Generators
          </motion.p>
        )}
      </AnimatePresence>

      {/* Dataset type buttons */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
        {Object.keys(datasetConfigs).map((key) => {
          const meta = categoryMeta[key];
          return (
            <button
              key={key}
              onClick={() => handleDatasetClick(key)}
              onMouseEnter={() => setHoveredKey(key)}
              onMouseLeave={() => setHoveredKey(null)}
              className={`
                group relative w-full flex items-center gap-3
                rounded-xl transition-all duration-200
                ${collapsed ? "px-2 py-2.5 justify-center" : "px-3 py-2.5"}
                hover:bg-white/[0.04]
              `}
            >
              {/* Icon */}
              <div className={`${meta?.accentColor || "text-zinc-400"} flex-shrink-0 transition-transform duration-200 group-hover:scale-110`}>
                <div className="w-5 h-5">
                  {meta?.icon || null}
                </div>
              </div>

              {/* Label */}
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -8 }}
                    transition={{ duration: 0.15 }}
                    className="text-[13px] font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors truncate"
                  >
                    {datasetConfigs[key].label}
                  </motion.span>
                )}
              </AnimatePresence>

              {/* Tooltip for collapsed state */}
              {collapsed && hoveredKey === key && (
                <div className="absolute left-full ml-3 px-3 py-1.5 bg-dark-300 rounded-lg text-xs text-zinc-200 font-medium whitespace-nowrap z-50 border border-white/[0.06] shadow-glass">
                  {datasetConfigs[key].label}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom nav */}
      <div className="px-3 pb-4 pt-2 border-t border-white/[0.04] space-y-0.5">
        <NavLink
          to="/pipeline"
          className={({ isActive }) =>
            `group relative flex items-center gap-3 rounded-xl transition-all duration-200
            ${collapsed ? "px-2 py-2.5 justify-center" : "px-3 py-2.5"}
            ${isActive ? "bg-primary/10 text-primary-300" : "hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200"}`
          }
        >
          <div className="flex-shrink-0">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center justify-between flex-1"
              >
                <span className="text-[13px] font-medium">Pipeline</span>
                {pendingCount > 0 && (
                  <span className="bg-primary/80 text-white text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center animate-pulse-glow">
                    {pendingCount}
                  </span>
                )}
              </motion.div>
            )}
          </AnimatePresence>
          {collapsed && pendingCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-primary text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {pendingCount}
            </span>
          )}
        </NavLink>

        <NavLink
          to="/datasets"
          className={({ isActive }) =>
            `group flex items-center gap-3 rounded-xl transition-all duration-200
            ${collapsed ? "px-2 py-2.5 justify-center" : "px-3 py-2.5"}
            ${isActive ? "bg-primary/10 text-primary-300" : "hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200"}`
          }
        >
          <div className="flex-shrink-0">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
            </svg>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[13px] font-medium"
              >
                View Datasets
              </motion.span>
            )}
          </AnimatePresence>
        </NavLink>
      </div>
    </motion.div>
  );
}