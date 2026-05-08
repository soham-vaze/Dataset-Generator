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
  { value: "sft", label: "SFT", color: "from-violet-500/20 to-purple-500/20", border: "border-violet-500/30" },
  { value: "nl_sql", label: "NL-SQL", color: "from-blue-500/20 to-indigo-500/20", border: "border-blue-500/30" },
  { value: "rag_qa", label: "RAG-QA", color: "from-cyan-500/20 to-teal-500/20", border: "border-cyan-500/30" },
  { value: "classification", label: "Classification", color: "from-amber-500/20 to-orange-500/20", border: "border-amber-500/30" },
  { value: "text_to_code", label: "Text-to-Code", color: "from-emerald-500/20 to-green-500/20", border: "border-emerald-500/30" },
  { value: "multilingual", label: "Multilingual", color: "from-pink-500/20 to-rose-500/20", border: "border-pink-500/30" },
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
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h2 className="text-2xl font-bold text-zinc-100 tracking-tight mb-2">
          Your Datasets
        </h2>
        <p className="text-zinc-500 text-sm">
          Browse, preview, and manage your generated datasets
        </p>
      </motion.div>

      {/* Type selector pills */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-wrap gap-2 mb-8"
      >
        {datasetTypes.map((type) => (
          <button
            key={type.value}
            onClick={() => setDatasetType(type.value)}
            className={`
              px-4 py-2 rounded-xl text-xs font-medium transition-all duration-300
              ${datasetType === type.value
                ? `bg-gradient-to-r ${type.color} ${type.border} border text-zinc-200 shadow-glow`
                : "bg-white/[0.03] border border-white/[0.06] text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.06]"
              }
            `}
          >
            {type.label}
          </button>
        ))}
      </motion.div>

      {/* Dataset list */}
      <div className="space-y-3 mb-8">
        <AnimatePresence mode="wait">
          {datasets.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
            >
              <GlassCard hover={false} className="py-16 text-center">
                <div className="mb-4">
                  <svg className="w-12 h-12 mx-auto text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
                  </svg>
                </div>
                <p className="text-zinc-400 font-medium">No datasets found</p>
                <p className="text-xs text-zinc-600 mt-2">
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
              className="space-y-3"
            >
              {datasets.map((dataset, i) => (
                <motion.div
                  key={dataset.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="group flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all duration-300"
                >
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-zinc-200 text-sm">
                      {dataset.name}
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-1.5 flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded-md bg-gradient-to-r ${currentType?.color || ""} text-zinc-300 font-medium`}>
                        {dataset.format}
                      </span>
                      <span>{new Date(dataset.created_at).toLocaleString()}</span>
                    </p>
                  </div>

                  <div className="flex gap-2 items-center flex-shrink-0">
                    <button
                      onClick={() => fetchCSV(dataset)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-primary/10 text-primary-300 border border-primary/20 hover:bg-primary/20 transition-all"
                    >
                      <Eye size={13} />
                      Preview
                    </button>

                    <button
                      onClick={() => openFullScreen(dataset)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"
                    >
                      <ExternalLink size={13} />
                      Full View
                    </button>

                    <button
                      onClick={() => deleteDataset(dataset.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all"
                    >
                      <Trash2 size={13} />
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
            className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="bg-dark-100 w-full max-w-[95%] h-[90vh] rounded-3xl shadow-glass-lg border border-white/[0.06] p-6 flex flex-col"
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-zinc-200">{selectedFile}</h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.08] transition-all"
                >
                  ✕
                </button>
              </div>

              <div
                className="ag-theme-alpine rounded-xl flex-1"
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
