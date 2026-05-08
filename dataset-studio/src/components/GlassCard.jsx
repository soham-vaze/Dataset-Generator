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
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={hover ? { y: -2, transition: { duration: 0.2 } } : {}}
      className={`
        relative rounded-3xl overflow-hidden
        bg-white/[0.03] backdrop-blur-xl
        border border-white/[0.06]
        shadow-glass
        transition-shadow duration-300
        ${hover ? "hover:shadow-glass-lg hover:border-white/[0.1]" : ""}
        ${gradient ? "gradient-border" : ""}
        ${className}
      `}
      {...props}
    >
      {children}
    </motion.div>
  );
}
