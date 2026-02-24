import { datasetConfigs } from "../config/datasetConfigs";
import {
  FileText,
  Database,
  Code,
  Globe,
  Layers,
  Folder,
} from "lucide-react";

export default function Sidebar({
  selectedDataset,
  setSelectedDataset,
  activePage,
  setActivePage,
}) {
  const icons = {
    sft: <FileText size={18} />,
    nl_sql: <Database size={18} />,
    rag_qa: <Layers size={18} />,
    classification: <FileText size={18} />,
    text_to_code: <Code size={18} />,
    multilingual: <Globe size={18} />,
  };

  return (
    <div className="w-72 bg-white/80 backdrop-blur-xl border-r border-zinc-200 p-6 shadow-sm relative">
      <h1 className="text-2xl font-bold mb-8 text-zinc-900 tracking-tight">
        Dataset Studio
      </h1>

      {/* ================= GENERATE SECTION ================= */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-zinc-400 uppercase mb-3">
          Generate
        </p>

        <div className="space-y-3">
          {Object.entries(datasetConfigs).map(([key, config]) => (
            <button
              key={key}
              onClick={() => {
                setSelectedDataset(key);
                setActivePage("generate");
              }}
              className={`w-full text-left px-4 py-3 rounded-2xl transition-all duration-200 flex items-center gap-3 ${
                activePage === "generate" && selectedDataset === key
                  ? "bg-indigo-600 text-white shadow-md"
                  : "hover:bg-zinc-100 text-zinc-700"
              }`}
            >
              {icons[key]}
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {/* ================= DATASETS SECTION ================= */}
      <div>
        <p className="text-xs font-semibold text-zinc-400 uppercase mb-3">
          Manage
        </p>

        <button
          onClick={() => setActivePage("datasets")}
          className={`w-full text-left px-4 py-3 rounded-2xl transition-all duration-200 flex items-center gap-3 ${
            activePage === "datasets"
              ? "bg-indigo-600 text-white shadow-md"
              : "hover:bg-zinc-100 text-zinc-700"
          }`}
        >
          <Folder size={18} />
          View Datasets
        </button>
      </div>

      <div className="absolute bottom-6 text-xs text-zinc-400">
        Dataset Studio v1.0
        <br />
        Research Internal Tool
      </div>
    </div>
  );
}