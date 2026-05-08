import { useState, useCallback } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { datasetConfigs } from "../config/datasetConfigs";
import { usePendingJobs } from "../context/PendingJobsContext";
import { categoryMeta } from "./CategoryCard";

/* ─── Floating tooltip with caret ─── */
function Tooltip({ children, visible }) {
  if (!visible) return null;
  return (
    <div className="absolute left-full ml-4 px-3.5 py-2 rounded-xl text-[12px] text-zinc-200 font-medium whitespace-nowrap z-[60] border border-white/[0.07] shadow-[0_8px_32px_rgba(0,0,0,0.5)] bg-[#151520]/95 backdrop-blur-2xl">
      {children}
      <div className="absolute left-0 top-1/2 -translate-x-[5px] -translate-y-1/2 w-[10px] h-[10px] bg-[#151520]/95 border-l border-b border-white/[0.07] rotate-45" />
    </div>
  );
}

/* ─── Glowing indicator beam ─── */
function ActiveBeam({ layoutId }) {
  return (
    <motion.div
      layoutId={layoutId}
      className="absolute left-0 top-1/2 -translate-y-1/2 w-[2.5px] h-6 rounded-r-full"
      style={{
        background: "linear-gradient(180deg, #a78bfa 0%, #7c3aed 50%, #6366f1 100%)",
        boxShadow: "0 0 12px 2px rgba(139,92,246,0.4), 0 0 4px 1px rgba(139,92,246,0.6)",
      }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
    />
  );
}

export default function Sidebar({ onSelectDataset, selectedDataset }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { myJobs } = usePendingJobs();
  const pendingCount = myJobs.filter((j) => j.status === "pending").length;
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredKey, setHoveredKey] = useState(null);
  const [hoveredNav, setHoveredNav] = useState(null);

  const handleDatasetClick = useCallback((key) => {
    onSelectDataset(key);
    navigate("/");
  }, [onSelectDataset, navigate]);

  const isHome = location.pathname === "/";

  const sidebarWidth = collapsed ? 68 : 252;

  return (
    <div className="relative z-30 flex-shrink-0" style={{ width: sidebarWidth }}>
      {/* Reserve layout space, then float the actual dock */}
      <motion.nav
        animate={{ width: sidebarWidth }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="fixed top-3 left-3 bottom-3 flex flex-col rounded-2xl overflow-hidden z-30"
        style={{
          background: "linear-gradient(165deg, rgba(14,14,22,0.85) 0%, rgba(10,10,16,0.92) 100%)",
          backdropFilter: "blur(40px) saturate(1.6)",
          WebkitBackdropFilter: "blur(40px) saturate(1.6)",
          border: "1px solid rgba(255,255,255,0.05)",
          boxShadow: `
            0 0 0 0.5px rgba(255,255,255,0.03) inset,
            0 1px 0 rgba(255,255,255,0.04) inset,
            0 20px 60px rgba(0,0,0,0.45),
            0 4px 16px rgba(0,0,0,0.3),
            0 0 1px rgba(0,0,0,0.6)
          `,
        }}
      >
        {/* ── Logo area ── */}
        <div className={`flex items-center gap-3 pt-5 pb-4 ${collapsed ? "px-3 justify-center" : "px-4"}`}>
          <motion.div
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.95 }}
            className="w-9 h-9 rounded-[11px] flex items-center justify-center flex-shrink-0 relative cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #3b82f6 100%)",
              boxShadow: "0 0 20px rgba(124,58,237,0.25), 0 2px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.15)",
            }}
            onClick={() => { onSelectDataset(null); navigate("/"); }}
          >
            <svg className="w-[18px] h-[18px] text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" opacity="0.45" />
              <path d="M2 12l10 5 10-5" opacity="0.65" />
            </svg>
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.18 }}
                className="min-w-0"
              >
                <h2 className="text-[13px] font-bold text-zinc-100 tracking-tight leading-tight">Dataset Studio</h2>
                <p className="text-[10px] text-zinc-600 font-medium mt-0.5">AI Dataset Generator</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Collapse toggle ── */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-[26px] w-[22px] h-[22px] rounded-full flex items-center justify-center z-50 group transition-all duration-200"
          style={{
            background: "linear-gradient(135deg, #15151f 0%, #111118 100%)",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
          }}
        >
          <motion.svg
            animate={{ rotate: collapsed ? 180 : 0 }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="w-[10px] h-[10px] text-zinc-500 group-hover:text-zinc-200 transition-colors duration-200"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </motion.svg>
        </button>

        {/* ── Separator ── */}
        <div className={`${collapsed ? "mx-3" : "mx-4"}`}>
          <div className="h-px" style={{ background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%)" }} />
        </div>

        {/* ── Section: Generators ── */}
        <AnimatePresence>
          {!collapsed && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="px-5 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 select-none"
            >
              Generators
            </motion.p>
          )}
        </AnimatePresence>

        {/* ── Generator items ── */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-px">
          {Object.keys(datasetConfigs).map((key) => {
            const meta = categoryMeta[key];
            const isActive = isHome && selectedDataset === key;
            const isHovered = hoveredKey === key;

            return (
              <motion.button
                key={key}
                onClick={() => handleDatasetClick(key)}
                onMouseEnter={() => setHoveredKey(key)}
                onMouseLeave={() => setHoveredKey(null)}
                whileHover={{ x: collapsed ? 0 : 2 }}
                transition={{ duration: 0.15 }}
                className={`
                  group relative w-full flex items-center
                  rounded-xl transition-all duration-200 outline-none
                  ${collapsed ? "px-0 py-2.5 justify-center" : "px-3 py-[9px] gap-3"}
                `}
                style={{
                  background: isActive
                    ? "rgba(139,92,246,0.08)"
                    : isHovered
                    ? "rgba(255,255,255,0.03)"
                    : "transparent",
                  border: isActive
                    ? "1px solid rgba(139,92,246,0.12)"
                    : "1px solid transparent",
                }}
              >
                {/* Active beam */}
                {isActive && <ActiveBeam layoutId="gen-active" />}

                {/* Icon container */}
                <motion.div
                  animate={{
                    scale: isActive ? 1.05 : isHovered ? 1.08 : 1,
                  }}
                  transition={{ duration: 0.2 }}
                  className="flex-shrink-0 relative"
                >
                  <div
                    className="w-[22px] h-[22px] transition-colors duration-200"
                    style={{
                      color: isActive
                        ? (meta?.accentHex || "#a78bfa")
                        : isHovered
                        ? (meta?.accentHex || "#a1a1aa")
                        : "#71717a",
                      filter: isActive
                        ? `drop-shadow(0 0 6px ${meta?.accentHex || "#a78bfa"}50)`
                        : "none",
                    }}
                  >
                    {meta?.icon || null}
                  </div>
                </motion.div>

                {/* Label */}
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -6 }}
                      transition={{ duration: 0.12 }}
                      className={`text-[13px] font-medium truncate transition-colors duration-150 ${
                        isActive ? "text-zinc-100" : "text-zinc-500 group-hover:text-zinc-300"
                      }`}
                    >
                      {datasetConfigs[key].label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {/* Collapsed tooltip */}
                {collapsed && (
                  <Tooltip visible={isHovered}>
                    {datasetConfigs[key].label}
                  </Tooltip>
                )}
              </motion.button>
            );
          })}
        </div>

        {/* ── Bottom separator ── */}
        <div className={`${collapsed ? "mx-3" : "mx-4"}`}>
          <div className="h-px" style={{ background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)" }} />
        </div>

        {/* ── Bottom navigation ── */}
        <div className="px-2 pb-3 pt-2 space-y-px">
          {/* Pipeline */}
          <NavLink
            to="/pipeline"
            onMouseEnter={() => setHoveredNav("pipeline")}
            onMouseLeave={() => setHoveredNav(null)}
            className={({ isActive }) =>
              `group relative flex items-center rounded-xl transition-all duration-200 outline-none
              ${collapsed ? "px-0 py-2.5 justify-center" : "px-3 py-[9px] gap-3"}`
            }
            style={({ isActive }) => ({
              background: isActive
                ? "rgba(139,92,246,0.07)"
                : hoveredNav === "pipeline"
                ? "rgba(255,255,255,0.025)"
                : "transparent",
              border: isActive
                ? "1px solid rgba(139,92,246,0.1)"
                : "1px solid transparent",
            })}
          >
            {({ isActive }) => (
              <>
                {isActive && <ActiveBeam layoutId="nav-active" />}
                <motion.div
                  animate={{ scale: hoveredNav === "pipeline" ? 1.08 : 1 }}
                  transition={{ duration: 0.2 }}
                  className="flex-shrink-0"
                >
                  <svg
                    className="w-[20px] h-[20px] transition-colors duration-200"
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"
                    style={{
                      color: isActive ? "#a78bfa" : hoveredNav === "pipeline" ? "#a1a1aa" : "#52525b",
                      filter: isActive ? "drop-shadow(0 0 6px rgba(167,139,250,0.4))" : "none",
                    }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                  </svg>
                </motion.div>
                <AnimatePresence>
                  {!collapsed && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.12 }}
                      className="flex items-center justify-between flex-1 min-w-0"
                    >
                      <span className={`text-[13px] font-medium transition-colors duration-150 ${isActive ? "text-zinc-200" : "text-zinc-500 group-hover:text-zinc-300"}`}>
                        Pipeline
                      </span>
                      {pendingCount > 0 && (
                        <span
                          className="text-white text-[9px] font-bold rounded-full w-[18px] h-[18px] flex items-center justify-center"
                          style={{
                            background: "linear-gradient(135deg, #7c3aed, #6366f1)",
                            boxShadow: "0 0 10px rgba(124,58,237,0.4)",
                          }}
                        >
                          {pendingCount}
                        </span>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
                {collapsed && pendingCount > 0 && (
                  <span
                    className="absolute -top-1 -right-1 text-white text-[8px] font-bold rounded-full w-[15px] h-[15px] flex items-center justify-center animate-pulse"
                    style={{
                      background: "linear-gradient(135deg, #7c3aed, #6366f1)",
                      boxShadow: "0 0 8px rgba(124,58,237,0.5)",
                    }}
                  >
                    {pendingCount}
                  </span>
                )}
                {collapsed && (
                  <Tooltip visible={hoveredNav === "pipeline"}>
                    Pipeline {pendingCount > 0 ? `(${pendingCount})` : ""}
                  </Tooltip>
                )}
              </>
            )}
          </NavLink>

          {/* View Datasets */}
          <NavLink
            to="/datasets"
            onMouseEnter={() => setHoveredNav("datasets")}
            onMouseLeave={() => setHoveredNav(null)}
            className={({ isActive }) =>
              `group relative flex items-center rounded-xl transition-all duration-200 outline-none
              ${collapsed ? "px-0 py-2.5 justify-center" : "px-3 py-[9px] gap-3"}`
            }
            style={({ isActive }) => ({
              background: isActive
                ? "rgba(139,92,246,0.07)"
                : hoveredNav === "datasets"
                ? "rgba(255,255,255,0.025)"
                : "transparent",
              border: isActive
                ? "1px solid rgba(139,92,246,0.1)"
                : "1px solid transparent",
            })}
          >
            {({ isActive }) => (
              <>
                {isActive && <ActiveBeam layoutId="nav-active" />}
                <motion.div
                  animate={{ scale: hoveredNav === "datasets" ? 1.08 : 1 }}
                  transition={{ duration: 0.2 }}
                  className="flex-shrink-0"
                >
                  <svg
                    className="w-[20px] h-[20px] transition-colors duration-200"
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"
                    style={{
                      color: isActive ? "#a78bfa" : hoveredNav === "datasets" ? "#a1a1aa" : "#52525b",
                      filter: isActive ? "drop-shadow(0 0 6px rgba(167,139,250,0.4))" : "none",
                    }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
                  </svg>
                </motion.div>
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.12 }}
                      className={`text-[13px] font-medium transition-colors duration-150 ${isActive ? "text-zinc-200" : "text-zinc-500 group-hover:text-zinc-300"}`}
                    >
                      View Datasets
                    </motion.span>
                  )}
                </AnimatePresence>
                {collapsed && (
                  <Tooltip visible={hoveredNav === "datasets"}>
                    View Datasets
                  </Tooltip>
                )}
              </>
            )}
          </NavLink>
        </div>

        {/* ── Ambient bottom glow ── */}
        <div
          className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3/4 h-20 pointer-events-none"
          style={{
            background: "radial-gradient(ellipse at center bottom, rgba(124,58,237,0.04) 0%, transparent 70%)",
          }}
        />
      </motion.nav>
    </div>
  );
}
