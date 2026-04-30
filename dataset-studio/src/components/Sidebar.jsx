import { NavLink, useNavigate } from "react-router-dom";
import { datasetConfigs } from "../config/datasetConfigs";
import { usePendingJobs } from "../context/PendingJobsContext";

export default function Sidebar({ onSelectDataset }) {
  const navigate = useNavigate();
  const { myJobs } = usePendingJobs();
  const pendingCount = myJobs.filter((j) => j.status === "pending").length;

  const handleDatasetClick = (key) => {
    onSelectDataset(key);
    navigate("/");
  };

  return (
    <div className="w-64 bg-white border-r border-zinc-200 p-6 flex flex-col">

      <h2 className="text-xl font-bold mb-6">Datasets</h2>

      <div className="space-y-2 flex-1">
        {Object.keys(datasetConfigs).map((key) => (
          <button
            key={key}
            onClick={() => handleDatasetClick(key)}
            className="w-full text-left px-4 py-2 rounded-lg hover:bg-indigo-100 text-zinc-700 transition"
          >
            {datasetConfigs[key].label}
          </button>
        ))}
      </div>

      <div className="pt-6 border-t border-zinc-200 space-y-1">
        <NavLink
          to="/pipeline"
          className={({ isActive }) =>
            `flex items-center justify-between px-4 py-2 rounded-lg hover:bg-indigo-100 text-zinc-700 transition ${isActive ? "bg-indigo-50 font-medium" : ""}`
          }
        >
          <span>Pipeline</span>
          {pendingCount > 0 && (
            <span className="bg-indigo-600 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
              {pendingCount}
            </span>
          )}
        </NavLink>
        <NavLink
          to="/datasets"
          className={({ isActive }) =>
            `block px-4 py-2 rounded-lg hover:bg-indigo-100 text-zinc-700 transition ${isActive ? "bg-indigo-50 font-medium" : ""}`
          }
        >
          View Datasets
        </NavLink>
      </div>
    </div>
  );
}