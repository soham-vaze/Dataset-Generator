import { motion } from "framer-motion";

export default function GlassCard({
  children,
  className = "",
  hover = true,
  gradient = false,
  delay = 0,
  ...props
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={hover ? { y: -3, transition: { duration: 0.25 } } : {}}
      className={`
        relative rounded-3xl overflow-hidden
        bg-gradient-to-b from-white/[0.03] to-white/[0.015]
        backdrop-blur-2xl
        border border-white/[0.06]
        shadow-glass
        transition-all duration-400
        ${hover ? "hover:shadow-glass-hover hover:border-white/[0.1]" : ""}
        ${gradient ? "gradient-border" : ""}
        ${className}
      `}
      {...props}
    >
      {/* Inner top highlight */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent pointer-events-none" />
      {children}
    </motion.div>
  );
}
