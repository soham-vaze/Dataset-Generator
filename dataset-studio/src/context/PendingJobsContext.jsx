import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useAuth } from "./AuthContext";

const API_BASE = import.meta.env.VITE_API_BASE_URL;
const PendingJobsContext = createContext();

export const PendingJobsProvider = ({ children }) => {
  const { userEmail, token } = useAuth();
  // jobs: { id, name, type, status: "pending"|"done"|"failed", startedAt, finishedAt?, error? }
  const [jobs, setJobs] = useState([]);

  const addJob = useCallback((id, name, type) => {
    setJobs((prev) => [
      { id, name, type, status: "pending", startedAt: new Date().toISOString(), userEmail },
      ...prev,
    ]);
  }, [userEmail]);

  const resolveJob = useCallback((id, success, error = null) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === id
          ? { ...j, status: success ? "done" : "failed", finishedAt: new Date().toISOString(), error }
          : j
      )
    );
  }, []);

  const updateJobId = useCallback((oldId, newId) => {
    setJobs((prev) => prev.map((j) => (j.id === oldId ? { ...j, id: newId } : j)));
  }, []);

  // Only jobs belonging to the currently logged-in user
  const myJobs = jobs.filter((j) => j.userEmail === userEmail);

  useEffect(() => {
    if (!token) return;
    const interval = setInterval(async () => {
      const pending = jobs.filter((j) => j.userEmail === userEmail && j.status === "pending");
      if (pending.length === 0) return;
      for (const job of pending) {
        try {
          const res = await fetch(`${API_BASE}/datasets/${job.id}/status`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await res.json();
          if (data.status !== "pending") {
            resolveJob(job.id, data.status === "ready");
          }
        } catch (e) { /* network error, retry next interval */ }
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [token, userEmail, jobs, resolveJob]);

  return (
    <PendingJobsContext.Provider value={{ myJobs, addJob, resolveJob, updateJobId }}>
      {children}
    </PendingJobsContext.Provider>
  );
};

export const usePendingJobs = () => useContext(PendingJobsContext);
