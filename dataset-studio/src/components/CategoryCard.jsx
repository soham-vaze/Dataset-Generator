import { motion } from "framer-motion";
import { useRef, useState } from "react";

const categoryMeta = {
  sft: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" strokeLinecap="round" />
        <path d="M12 6v6l4 2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.5" />
        <path d="M8 14l-2 4M16 14l2 4M12 16v4" strokeLinecap="round" opacity="0.5" />
      </svg>
    ),
    gradient: "from-violet-500/20 via-purple-500/10 to-fuchsia-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(139,92,246,0.15)]",
    accentColor: "text-violet-400",
    accentHex: "#8b5cf6",
    description: "Generate instruction-response pairs for supervised fine-tuning",
    bgAccent: "bg-violet-500/10",
    tag: "SFT",
  },
  nl_sql: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 7h16M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7M4 7l2-3h12l2 3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 12h2M14 12h2M8 15h8" strokeLinecap="round" opacity="0.7" />
      </svg>
    ),
    gradient: "from-blue-500/20 via-indigo-500/10 to-cyan-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(59,130,246,0.15)]",
    accentColor: "text-blue-400",
    accentHex: "#3b82f6",
    description: "Convert natural language queries into SQL statements",
    bgAccent: "bg-blue-500/10",
    tag: "NL-SQL",
  },
  rag_qa: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="8" r="4" />
        <circle cx="6" cy="18" r="3" opacity="0.5" />
        <circle cx="18" cy="18" r="3" opacity="0.5" />
        <path d="M12 12v3M9 15.5l-1.5 1M15 15.5l1.5 1" strokeLinecap="round" />
      </svg>
    ),
    gradient: "from-cyan-500/20 via-teal-500/10 to-emerald-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(6,182,212,0.15)]",
    accentColor: "text-cyan-400",
    accentHex: "#06b6d4",
    description: "Build question-answer pairs from document context",
    bgAccent: "bg-cyan-500/10",
    tag: "RAG-QA",
  },
  classification: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <rect x="3" y="3" width="7" height="7" rx="2" />
        <rect x="14" y="3" width="7" height="7" rx="2" opacity="0.7" />
        <rect x="3" y="14" width="7" height="7" rx="2" opacity="0.5" />
        <rect x="14" y="14" width="7" height="7" rx="2" opacity="0.3" />
      </svg>
    ),
    gradient: "from-amber-500/20 via-orange-500/10 to-rose-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(245,158,11,0.15)]",
    accentColor: "text-amber-400",
    accentHex: "#f59e0b",
    description: "Generate labeled data for text classification tasks",
    bgAccent: "bg-amber-500/10",
    tag: "Classification",
  },
  text_to_code: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <polyline points="16,18 22,12 16,6" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="8,6 2,12 8,18" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="14" y1="4" x2="10" y2="20" opacity="0.5" strokeLinecap="round" />
      </svg>
    ),
    gradient: "from-emerald-500/20 via-green-500/10 to-teal-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(16,185,129,0.15)]",
    accentColor: "text-emerald-400",
    accentHex: "#10b981",
    description: "Transform natural language descriptions into code",
    bgAccent: "bg-emerald-500/10",
    tag: "Code",
  },
  multilingual: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="10" />
        <ellipse cx="12" cy="12" rx="4" ry="10" />
        <path d="M2 12h20" strokeLinecap="round" />
        <path d="M4 7h16M4 17h16" strokeLinecap="round" opacity="0.4" />
      </svg>
    ),
    gradient: "from-pink-500/20 via-rose-500/10 to-purple-500/5",
    glow: "group-hover:shadow-[0_8px_50px_rgba(236,72,153,0.15)]",
    accentColor: "text-pink-400",
    accentHex: "#ec4899",
    description: "Create parallel translation datasets across languages",
    bgAccent: "bg-pink-500/10",
    tag: "Multilingual",
  },
};

export { categoryMeta };

export default function CategoryCard({ configKey, label, onClick, index = 0 }) {
  const meta = categoryMeta[configKey] || categoryMeta.sft;
  const cardRef = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({
      x: (y - 0.5) * -8,
      y: (x - 0.5) * 8,
    });
    setGlowPos({ x: x * 100, y: y * 100 });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 0, y: 0 });
    setGlowPos({ x: 50, y: 50 });
  };

  return (
    <motion.button
      ref={cardRef}
      onClick={onClick}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.5,
        delay: index * 0.08,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileTap={{ scale: 0.97 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: `perspective(800px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
        transition: "transform 0.15s ease-out",
      }}
      className={`
        group relative w-full text-left
        rounded-2xl overflow-hidden
        bg-gradient-to-br ${meta.gradient}
        border border-white/[0.06]
        backdrop-blur-xl
        p-6 cursor-pointer
        transition-all duration-500
        ${meta.glow}
        hover:border-white/[0.12]
      `}
    >
      {/* Cursor-reactive glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(400px circle at ${glowPos.x}% ${glowPos.y}%, ${meta.accentHex}08, transparent 60%)`,
        }}
      />

      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent group-hover:via-white/[0.15] transition-all duration-500" />

      <div className="relative z-10">
        {/* Icon + tag row */}
        <div className="flex items-start justify-between mb-4">
          <div className={`${meta.accentColor} transition-transform duration-300 group-hover:scale-110`}>
            {meta.icon}
          </div>
          <span className={`text-[10px] font-semibold uppercase tracking-[0.1em] px-2.5 py-1 rounded-lg ${meta.bgAccent} ${meta.accentColor} opacity-60 group-hover:opacity-100 transition-opacity`}>
            {meta.tag}
          </span>
        </div>

        {/* Label */}
        <h3 className="text-[15px] font-semibold text-zinc-100 mb-2 tracking-[-0.01em] group-hover:text-white transition-colors">
          {label}
        </h3>

        {/* Description */}
        <p className="text-[12px] text-zinc-500 leading-relaxed line-clamp-2 group-hover:text-zinc-400 transition-colors">
          {meta.description}
        </p>

        {/* Arrow indicator */}
        <div className="mt-5 flex items-center gap-2 text-[12px] text-zinc-600 group-hover:text-zinc-300 transition-colors">
          <span className="font-medium">Generate</span>
          <svg className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </div>
      </div>
    </motion.button>
  );
}
