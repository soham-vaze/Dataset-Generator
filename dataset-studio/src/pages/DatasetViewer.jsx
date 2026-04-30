import { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import { useAuth } from "../context/AuthContext";

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
      <div className="flex items-center justify-center h-screen text-zinc-500 text-lg">
        Loading dataset…
      </div>
    );

  if (error)
    return (
      <div className="flex items-center justify-center h-screen text-red-500 text-lg">
        {error}
      </div>
    );

  return (
    <div className="flex flex-col h-screen bg-zinc-50 p-6">
      <h2 className="text-2xl font-bold text-zinc-800 mb-4">{datasetName}</h2>
      <div className="ag-theme-alpine rounded-xl flex-1" style={{ width: "100%" }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          pagination
          paginationPageSize={50}
        />
      </div>
    </div>
  );
}
