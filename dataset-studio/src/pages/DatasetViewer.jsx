import { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import { useAuth } from "../context/AuthContext";
import AnimatedBackground from "../components/AnimatedBackground";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

ModuleRegistry.registerModules([AllCommunityModule]);

const BASE_URL = "http://localhost:8000";

function parseCSV(csvText) {
  const rows = [];
  let current = "";
  let inQuotes = false;
  const chars = csvText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  let row = [];
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    if (ch === '"') {
      if (inQuotes && chars[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      row.push(current);
      current = "";
    } else if (ch === "\n" && !inQuotes) {
      row.push(current);
      rows.push(row);
      row = [];
      current = "";
    } else {
      current += ch;
    }
  }
  if (current || row.length) {
    row.push(current);
    if (row.some((c) => c !== "")) rows.push(row);
  }

  if (rows.length === 0) return { columnDefs: [], rowData: [] };

  const headers = rows[0];
  const columnDefs = headers.map((h) => ({ headerName: h, field: h, tooltipField: h }));
  const rowData = rows.slice(1).map((r) => {
    const obj = {};
    headers.forEach((h, i) => (obj[h] = r[i] ?? ""));
    return obj;
  });

  return { columnDefs, rowData };
}

export default function DatasetViewer() {
  const { datasetId } = useParams();
  const { token } = useAuth();
  const [columnDefs, setColumnDefs] = useState([]);
  const [rowData, setRowData] = useState([]);
  const [datasetName, setDatasetName] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const defaultColDef = useMemo(
    () => ({ sortable: true, filter: true, resizable: true, flex: 1, wrapText: true, autoHeight: true }),
    []
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/datasets/${datasetId}`, {
          headers: { Authorization: `Bearer ${token}` },
          responseType: "text",
        });
        const name = res.headers["content-disposition"]
          ?.split("filename=")[1]
          ?.replace(/"/g, "") ?? datasetId;
        setDatasetName(name);
        const { columnDefs, rowData } = parseCSV(res.data);
        setColumnDefs(columnDefs);
        setRowData(rowData);
      } catch (err) {
        setError("Failed to load dataset.");
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [datasetId, token]);

  if (loading)
    return (
      <div className="flex items-center justify-center h-screen bg-dark">
        <AnimatedBackground />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="relative z-10 flex flex-col items-center gap-4"
        >
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center">
            <svg className="animate-spin w-5 h-5 text-primary-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <p className="text-zinc-500 text-sm font-medium">Loading dataset…</p>
        </motion.div>
      </div>
    );

  if (error)
    return (
      <div className="flex items-center justify-center h-screen bg-dark">
        <AnimatedBackground />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="relative z-10 text-center"
        >
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-red-400 text-sm">{error}</p>
        </motion.div>
      </div>
    );

  return (
    <div className="flex flex-col h-screen bg-dark">
      <AnimatedBackground />
      <div className="relative z-10 flex flex-col h-full p-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 mb-4"
        >
          <div className="w-8 h-8 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center">
            <svg className="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-zinc-100 tracking-tight">{datasetName}</h2>
            <p className="text-[11px] text-zinc-500">{rowData.length} rows · {columnDefs.length} columns</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="ag-theme-alpine rounded-2xl flex-1 border border-white/[0.06] overflow-hidden"
          style={{ width: "100%" }}
        >
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            pagination
            paginationPageSize={50}
          />
        </motion.div>
      </div>
    </div>
  );
}
