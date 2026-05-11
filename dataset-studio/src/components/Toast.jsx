import { motion, AnimatePresence } from "framer-motion";
import { useNotification } from "../context/NotificationContext";
import { CheckCircle, XCircle, X } from "lucide-react";

export default function Toast() {
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      <AnimatePresence mode="popLayout">
        {notifications.map((notif) => (
          <motion.div
            key={notif.id}
            initial={{ opacity: 0, y: 16, scale: 0.96, x: 20 }}
            animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.96, x: 20, transition: { duration: 0.2 } }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className={`
              pointer-events-auto relative overflow-hidden
              flex items-start gap-3 p-4 rounded-2xl
              backdrop-blur-2xl shadow-glass border text-sm
              ${notif.type === "success"
                ? "bg-emerald-500/[0.06] border-emerald-500/[0.15] text-zinc-200"
                : "bg-red-500/[0.06] border-red-500/[0.15] text-zinc-200"
              }
            `}
          >
            {/* Top accent */}
            <div className={`absolute top-0 left-0 right-0 h-px ${
              notif.type === "success"
                ? "bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent"
                : "bg-gradient-to-r from-transparent via-red-500/30 to-transparent"
            }`} />

            <div className="mt-0.5 shrink-0">
              {notif.type === "success" ? (
                <CheckCircle className="w-[18px] h-[18px] text-emerald-400" />
              ) : (
                <XCircle className="w-[18px] h-[18px] text-red-400" />
              )}
            </div>
            <p className="flex-1 leading-relaxed text-[13px] text-zinc-300">{notif.message}</p>
            <button
              onClick={() => removeNotification(notif.id)}
              className="shrink-0 text-zinc-600 hover:text-zinc-300 transition-colors duration-200 mt-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
