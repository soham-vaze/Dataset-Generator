import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2, Eye, ExternalLink } from "lucide-react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import { useAuth } from "../context/AuthContext";
import GlassCard from "../components/GlassCard";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

ModuleRegistry.registerModules([AllCommunityModule]);

const datasetTypes = [
  { value: "sft", label: "SFT", accent: "text-violet-400", bg: "bg-violet-500/[0.08]", border: "border-violet-500/20", activeBg: "from-violet-500/20 to-purple-500/10" },
  { value: "nl_sql", label: "NL-SQL", accent: "text-blue-400", bg: "bg-blue-500/[0.08]", border: "border-blue-500/20", activeBg: "from-blue-500/20 to-indigo-500/10" },
  { value: "rag_qa", label: "RAG-QA", accent: "text-cyan-400", bg: "bg-cyan-500/[0.08]", border: "border-cyan-500/20", activeBg: "from-cyan-500/20 to-teal-500/10" },
  { value: "classification", label: "Classification", accent: "text-amber-400", bg: "bg-amber-500/[0.08]", border: "border-amber-500/20", activeBg: "from-amber-500/20 to-orange-500/10" },
  { value: "text_to_code", label: "Code", accent: "text-emerald-400", bg: "bg-emerald-500/[0.08]", border: "border-emerald-500/20", activeBg: "from-emerald-500/20 to-green-500/10" },
  { value: "multilingual", label: "Multilingual", accent: "text-pink-400", bg: "bg-pink-500/[0.08]", border: "border-pink-500/20", activeBg: "from-pink-500/20 to-rose-500/10" },
  { value: "multilingual_ft", label: "Multilingual FT", accent: "text-fuchsia-400", bg: "bg-fuchsia-500/[0.08]", border: "border-fuchsia-500/20", activeBg: "from-fuchsia-500/20 to-purple-500/10" },
];

export default function DatasetsPage() {
  const { token } = useAuth();
  const [datasetType, setDatasetType] = useState("sft");
  const [datasets, setDatasets] = useState([]);
  const [rowData, setRowData] = useState([]);
  const [columnDefs, setColumnDefs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState("");

  const BASE_URL = "http://localhost:8000";

  const defaultColDef = useMemo(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
      flex: 1,
    }),
    []
  );

  const fetchDatasets = async () => {
    const res = await axios.get(
      `${BASE_URL}/datasets?dataset_type=${datasetType}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    setDatasets(res.data.datasets);
  };

  useEffect(() => {
    fetchDatasets();
  }, [datasetType]);

  const fetchCSV = async (dataset) => {
    try {
      const res = await axios.get(`${BASE_URL}/datasets/${dataset.id}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "text",
      });
      parseCSV(res.data);
      setSelectedFile(dataset.name);
      setShowModal(true);
    } catch (err) {
      console.error("Error fetching CSV:", err);
    }
  };

  const openFullScreen = (dataset) => {
    window.open(`/view-dataset/${dataset.id}`, "_blank");
  };

  const parseCSV = (csvText) => {
    const rows = [];
    let current = "";
    let inQuotes = false;
    const text = csvText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    let row = [];

    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (ch === '"') {
        if (inQuotes && text[i + 1] === '"') { current += '"'; i++; }
        else inQuotes = !inQuotes;
      } else if (ch === "," && !inQuotes) {
        row.push(current); current = "";
      } else if (ch === "\n" && !inQuotes) {
        row.push(current); rows.push(row); row = []; current = "";
      } else {
        current += ch;
      }
    }
    if (current || row.length) { row.push(current); if (row.some(Boolean)) rows.push(row); }

    if (!rows.length) return;
    const headers = rows[0];
    const cols = headers.map((h) => ({ headerName: h, field: h, tooltipField: h }));
    const formattedRows = rows.slice(1).map((r) => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = r[i] ?? ""; });
      return obj;
    });
    setColumnDefs(cols);
    setRowData(formattedRows);
  };

  const deleteDataset = async (datasetId) => {
    try {
      await axios.delete(`${BASE_URL}/datasets/${datasetId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchDatasets();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const currentType = datasetTypes.find(t => t.value === datasetType);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ease: [0.25, 0.46, 0.45, 0.94] }}
        className="mb-8"
      >
        <h2 className="text-2xl font-bold text-zinc-100 tracking-[-0.02em] mb-2">
          Your Datasets
        </h2>
        <p className="text-zinc-500 text-sm">
          Browse, preview, and manage your generated datasets
        </p>
      </motion.div>

      {/* Type selector */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-wrap gap-2 mb-8"
      >
        {datasetTypes.map((type) => {
          const isActive = datasetType === type.value;
          return (
            <button
              key={type.value}
              onClick={() => setDatasetType(type.value)}
              className={`
                relative px-4 py-2 rounded-xl text-[12px] font-semibold transition-all duration-300
                ${isActive
                  ? `bg-gradient-to-r ${type.activeBg} border ${type.border} ${type.accent}`
                  : "bg-white/[0.02] border border-white/[0.05] text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.05] hover:border-white/[0.08]"
                }
              `}
            >
              {type.label}
              {isActive && (
                <motion.div
                  layoutId="dataset-type-indicator"
                  className="absolute inset-0 rounded-xl ring-1 ring-white/[0.08]"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </motion.div>

      {/* Dataset list */}
      <div className="space-y-3 mb-8">
        <AnimatePresence mode="wait">
          {datasets.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
            >
              <GlassCard hover={false} className="py-20 text-center">
                <div className="mb-5">
                  <svg className="w-14 h-14 mx-auto text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="0.75">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
                  </svg>
                </div>
                <p className="text-zinc-400 font-medium text-[15px]">No datasets found</p>
                <p className="text-[12px] text-zinc-600 mt-2">
                  No {currentType?.label || datasetType.toUpperCase()} datasets have been generated yet.
                </p>
              </GlassCard>
            </motion.div>
          ) : (
            <motion.div
              key={datasetType}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2.5"
            >
              {datasets.map((dataset, i) => (
                <motion.div
                  key={dataset.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="group flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-5 rounded-2xl bg-white/[0.015] border border-white/[0.05] hover:bg-white/[0.035] hover:border-white/[0.1] transition-all duration-300"
                >
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-zinc-200 text-sm group-hover:text-white transition-colors">
                      {dataset.name}
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-1.5 flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded-md ${currentType?.bg || ""} ${currentType?.accent || "text-zinc-400"} font-semibold text-[10px] uppercase tracking-wider`}>
                        {dataset.format}
                      </span>
                      <span>{new Date(dataset.created_at).toLocaleString()}</span>
                    </p>
                  </div>

                  <div className="flex gap-1.5 items-center flex-shrink-0">
                    <button
                      onClick={() => fetchCSV(dataset)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-primary/[0.08] text-primary-300 border border-primary/[0.15] hover:bg-primary/[0.15] hover:border-primary/[0.25] transition-all duration-200"
                    >
                      <Eye size={12} />
                      Preview
                    </button>

                    <button
                      onClick={() => openFullScreen(dataset)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-emerald-500/[0.08] text-emerald-400 border border-emerald-500/[0.15] hover:bg-emerald-500/[0.15] hover:border-emerald-500/[0.25] transition-all duration-200"
                    >
                      <ExternalLink size={12} />
                      Full View
                    </button>

                    <button
                      onClick={() => deleteDataset(dataset.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-lg bg-red-500/[0.06] text-red-400/80 border border-red-500/[0.1] hover:bg-red-500/[0.12] hover:border-red-500/[0.2] hover:text-red-400 transition-all duration-200"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* MODAL */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-xl flex items-center justify-center z-50 p-4"
            onClick={(e) => e.target === e.currentTarget && setShowModal(false)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0, y: 12 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.96, opacity: 0, y: 12 }}
              transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="bg-dark-100 w-full max-w-[95%] h-[90vh] rounded-3xl shadow-glass-lg border border-white/[0.06] p-6 flex flex-col relative overflow-hidden"
            >
              {/* Top accent */}
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />

              <div className="flex justify-between items-center mb-5">
                <div>
                  <h3 className="text-lg font-semibold text-zinc-200 tracking-tight">{selectedFile}</h3>
                  <p className="text-[11px] text-zinc-600 mt-0.5">{rowData.length} rows · {columnDefs.length} columns</p>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.08] hover:border-white/[0.1] transition-all duration-200"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div
                className="ag-theme-alpine rounded-2xl flex-1 overflow-hidden"
                style={{ height: "100%", width: "100%" }}
              >
                <AgGridReact
                  rowData={rowData}
                  columnDefs={columnDefs}
                  defaultColDef={defaultColDef}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
