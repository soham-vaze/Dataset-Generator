import { motion } from "framer-motion";

export default function StepIndicator({ steps, currentStep }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {steps.map((step, i) => {
        const isActive = i === currentStep;
        const isCompleted = i < currentStep;

        return (
          <div key={i} className="flex items-center gap-2">
            {/* Step circle */}
            <motion.div
              animate={{
                scale: isActive ? 1.1 : 1,
                backgroundColor: isCompleted
                  ? "rgba(124, 58, 237, 0.8)"
                  : isActive
                  ? "rgba(124, 58, 237, 0.4)"
                  : "rgba(255, 255, 255, 0.04)",
              }}
              className={`
                w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium
                border transition-colors duration-300
                ${isCompleted
                  ? "border-primary/40 text-white"
                  : isActive
                  ? "border-primary/50 text-white"
                  : "border-white/[0.06] text-zinc-500"
                }
              `}
            >
              {isCompleted ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                i + 1
              )}
            </motion.div>

            {/* Step label */}
            <span
              className={`text-xs font-medium hidden sm:block ${
                isActive ? "text-zinc-200" : "text-zinc-500"
              }`}
            >
              {step}
            </span>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className="w-8 sm:w-12 h-px bg-white/[0.06] mx-1">
                <motion.div
                  animate={{ width: isCompleted ? "100%" : "0%" }}
                  className="h-full bg-primary/40"
                  transition={{ duration: 0.3 }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
