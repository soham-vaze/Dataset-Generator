import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const SUGGESTIONS = [
  "spam, ham",
  "positive, negative, neutral",
  "billing, technical_issue, account_access",
  "bug, feature, question",
  "urgent, normal, low_priority",
];

export default function TagInput({ tags = [], onChange, maxTags = 50 }) {
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const addTag = (value) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (trimmed.length > 100) {
      setError("Label too long (max 100 characters)");
      return;
    }
    if (!/^[a-zA-Z0-9\-_ ]+$/.test(trimmed)) {
      setError("Only letters, numbers, hyphens, underscores, and spaces allowed");
      return;
    }
    if (tags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) {
      setError(`"${trimmed}" already added`);
      return;
    }
    if (tags.length >= maxTags) {
      setError(`Maximum ${maxTags} labels allowed`);
      return;
    }
    setError("");
    onChange([...tags, trimmed]);
  };

  const removeTag = (index) => {
    onChange(tags.filter((_, i) => i !== index));
    setError("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const parts = input.split(",").map((s) => s.trim()).filter(Boolean);
      parts.forEach(addTag);
      setInput("");
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text");
    const parts = pasted.split(",").map((s) => s.trim()).filter(Boolean);
    parts.forEach(addTag);
    setInput("");
  };

  const applySuggestion = (suggestion) => {
    const parts = suggestion.split(",").map((s) => s.trim()).filter(Boolean);
    const newTags = [];
    parts.forEach((t) => {
      if (!tags.some((existing) => existing.toLowerCase() === t.toLowerCase()) && newTags.length + tags.length < maxTags) {
        newTags.push(t);
      }
    });
    if (newTags.length > 0) {
      onChange([...tags, ...newTags]);
    }
    setError("");
  };

  const isValid = tags.length >= 2;

  return (
    <div className="space-y-2.5">
      {/* Tag input container */}
      <div
        onClick={() => inputRef.current?.focus()}
        className="glass-input w-full !p-3 flex flex-wrap items-center gap-2 cursor-text min-h-[52px]"
      >
        <AnimatePresence mode="popLayout">
          {tags.map((tag, i) => (
            <motion.span
              key={tag}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         bg-primary/[0.12] text-primary-300 border border-primary/[0.2]
                         hover:bg-primary/[0.18] hover:border-primary/[0.35] transition-all duration-200 group"
            >
              <span>{tag}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeTag(i); }}
                className="w-4 h-4 flex items-center justify-center rounded-full
                           text-primary-400/60 hover:text-red-400 hover:bg-red-400/[0.15]
                           transition-all duration-200"
                aria-label={`Remove ${tag}`}
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </motion.span>
          ))}
        </AnimatePresence>

        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => { setInput(e.target.value); setError(""); }}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={tags.length === 0 ? "Type a label and press Enter..." : "Add more..."}
          className="flex-1 min-w-[120px] bg-transparent border-none outline-none text-sm text-zinc-200 placeholder:text-zinc-600"
        />
      </div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-[11px] text-red-400 flex items-center gap-1.5"
          >
            <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Validation hint */}
      <div className="flex items-center justify-between">
        <p className={`text-[11px] flex items-center gap-1.5 ${isValid ? "text-emerald-500/70" : "text-zinc-600"}`}>
          {isValid ? (
            <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
          )}
          {tags.length} label{tags.length !== 1 ? "s" : ""} added{!isValid && " — minimum 2 required"}
        </p>
        <p className="text-[11px] text-zinc-600">
          Press <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-zinc-500 font-mono text-[10px]">Enter</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-zinc-500 font-mono text-[10px]">,</kbd> to add
        </p>
      </div>

      {/* Quick suggestions */}
      {tags.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-2"
        >
          <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-[0.08em]">Quick suggestions</p>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => applySuggestion(s)}
                className="px-2.5 py-1 rounded-lg text-[11px] text-zinc-500
                           bg-white/[0.025] border border-white/[0.05]
                           hover:bg-white/[0.05] hover:border-white/[0.1] hover:text-zinc-300
                           transition-all duration-200"
              >
                {s}
              </button>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
