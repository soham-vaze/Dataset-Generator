import { createContext, useContext, useState, useCallback } from "react";
import { useAuth } from "./AuthContext";

const PendingJobsContext = createContext();

export const PendingJobsProvider = ({ children }) => {
  const { userEmail } = useAuth();
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

  // Only jobs belonging to the currently logged-in user
  const myJobs = jobs.filter((j) => j.userEmail === userEmail);

  return (
    <PendingJobsContext.Provider value={{ myJobs, addJob, resolveJob }}>
      {children}
    </PendingJobsContext.Provider>
  );
};

export const usePendingJobs = () => useContext(PendingJobsContext);
