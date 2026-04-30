import { useNotification } from "../context/NotificationContext";
import { CheckCircle, XCircle, X } from "lucide-react";

export default function Toast() {
  const { notifications, removeNotification } = useNotification();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full">
      {notifications.map((notif) => (
        <div
          key={notif.id}
          className={`flex items-start gap-3 p-4 rounded-2xl shadow-xl border text-sm animate-fade-in ${
            notif.type === "success"
              ? "bg-white border-green-200 text-zinc-800"
              : "bg-white border-red-200 text-zinc-800"
          }`}
        >
          <div className="mt-0.5 shrink-0">
            {notif.type === "success" ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p className="flex-1 leading-snug">{notif.message}</p>
          <button
            onClick={() => removeNotification(notif.id)}
            className="shrink-0 text-zinc-400 hover:text-zinc-600 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
