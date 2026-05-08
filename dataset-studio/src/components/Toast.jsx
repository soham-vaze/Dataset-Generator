import { motion, AnimatePresence } from "framer-motion";
import { useNotification } from "../context/NotificationContext";
import { CheckCircle, XCircle, X } from "lucide-react";

export default function Toast() {
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      <AnimatePresence mode="popLayout">
        {notifications.map((notif) => (
          <motion.div
            key={notif.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className={`
              pointer-events-auto
              flex items-start gap-3 p-4 rounded-2xl
              backdrop-blur-xl shadow-glass border text-sm
              ${notif.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-zinc-200"
                : "bg-red-500/10 border-red-500/20 text-zinc-200"
              }
            `}
          >
            <div className="mt-0.5 shrink-0">
              {notif.type === "success" ? (
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-400" />
              )}
            </div>
            <p className="flex-1 leading-snug text-zinc-300">{notif.message}</p>
            <button
              onClick={() => removeNotification(notif.id)}
              className="shrink-0 text-zinc-500 hover:text-zinc-300 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
