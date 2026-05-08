import { motion } from "framer-motion";

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
    gradient: "from-violet-500/20 via-purple-500/10 to-fuchsia-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(139,92,246,0.15)]",
    accentColor: "text-violet-400",
    description: "Generate instruction-response pairs for supervised fine-tuning",
    bgAccent: "bg-violet-500/10",
  },
  nl_sql: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 7h16M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7M4 7l2-3h12l2 3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 12h2M14 12h2M8 15h8" strokeLinecap="round" opacity="0.7" />
      </svg>
    ),
    gradient: "from-blue-500/20 via-indigo-500/10 to-cyan-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(59,130,246,0.15)]",
    accentColor: "text-blue-400",
    description: "Convert natural language queries into SQL statements",
    bgAccent: "bg-blue-500/10",
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
    gradient: "from-cyan-500/20 via-teal-500/10 to-emerald-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(6,182,212,0.15)]",
    accentColor: "text-cyan-400",
    description: "Build question-answer pairs from document context",
    bgAccent: "bg-cyan-500/10",
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
    gradient: "from-amber-500/20 via-orange-500/10 to-rose-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(245,158,11,0.15)]",
    accentColor: "text-amber-400",
    description: "Generate labeled data for text classification tasks",
    bgAccent: "bg-amber-500/10",
  },
  text_to_code: {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-8 h-8" stroke="currentColor" strokeWidth="1.5">
        <polyline points="16,18 22,12 16,6" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="8,6 2,12 8,18" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="14" y1="4" x2="10" y2="20" opacity="0.5" strokeLinecap="round" />
      </svg>
    ),
    gradient: "from-emerald-500/20 via-green-500/10 to-teal-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(16,185,129,0.15)]",
    accentColor: "text-emerald-400",
    description: "Transform natural language descriptions into code",
    bgAccent: "bg-emerald-500/10",
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
    gradient: "from-pink-500/20 via-rose-500/10 to-purple-500/20",
    glow: "group-hover:shadow-[0_0_40px_rgba(236,72,153,0.15)]",
    accentColor: "text-pink-400",
    description: "Create parallel translation datasets across languages",
    bgAccent: "bg-pink-500/10",
  },
};

export { categoryMeta };

export default function CategoryCard({ configKey, label, onClick, index = 0 }) {
  const meta = categoryMeta[configKey] || categoryMeta.sft;

  return (
    <motion.button
      onClick={onClick}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.5,
        delay: index * 0.08,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{ y: -4, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
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
      {/* Subtle inner glow on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <div className="relative z-10">
        {/* Icon */}
        <div className={`${meta.accentColor} mb-4 transition-transform duration-300 group-hover:scale-110`}>
          {meta.icon}
        </div>

        {/* Label */}
        <h3 className="text-[15px] font-semibold text-zinc-100 mb-1.5 tracking-tight">
          {label}
        </h3>

        {/* Description */}
        <p className="text-xs text-zinc-400 leading-relaxed line-clamp-2">
          {meta.description}
        </p>

        {/* Arrow indicator */}
        <div className="mt-4 flex items-center gap-1.5 text-xs text-zinc-500 group-hover:text-zinc-300 transition-colors">
          <span>Generate</span>
          <svg className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </motion.button>
  );
}
