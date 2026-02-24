import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { Trash2, Eye, ExternalLink } from "lucide-react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

ModuleRegistry.registerModules([AllCommunityModule]);

export default function DatasetsPage() {
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
      `${BASE_URL}/datasets?dataset_type=${datasetType}`
    );
    setDatasets(res.data.datasets);
  };

  useEffect(() => {
    fetchDatasets();
  }, [datasetType]);

  const fetchCSV = async (filename) => {
    const res = await axios.get(
      `${BASE_URL}/datasets/${datasetType}/${filename}`
    );

    console.log("CSV Response:", res.data);

    parseCSV(res.data);
    setSelectedFile(filename);
    setShowModal(true);
  };

  const openFullScreen = (filename) => {
    const url = `${BASE_URL}/datasets/${datasetType}/${filename}`;
    window.open(url, "_blank");
  };

  const parseCSV = (csvText) => {
    const rows = csvText.trim().split("\n").map((row) => row.split(","));

    if (!rows.length) return;

    const headers = rows[0];
    const dataRows = rows.slice(1);

    console.log("Headers:", headers);
    console.log("Data rows:", dataRows);

    const cols = headers.map((header) => ({
      headerName: header,
      field: header,
    }));

    const formattedRows = dataRows.map((row) => {
      let obj = {};
      headers.forEach((header, i) => {
        obj[header] = row[i] || "";
      });
      return obj;
    });

    setColumnDefs(cols);
    setRowData(formattedRows);
  };

  const deleteDataset = async (filename) => {
    await axios.delete(
      `${BASE_URL}/datasets/${datasetType}/${filename}`
    );
    fetchDatasets();
  };

  return (
    <div className="p-8 w-full">
      <h2 className="text-2xl font-bold mb-6 text-zinc-800">
        View Generated Datasets
      </h2>

      {/* Dataset Type Selector */}
      <select
        value={datasetType}
        onChange={(e) => setDatasetType(e.target.value)}
        className="mb-6 p-3 rounded-xl border border-zinc-300"
      >
        <option value="sft">SFT</option>
        <option value="nl_sql">NL-SQL</option>
        <option value="rag_qa">RAG-QA</option>
        <option value="classification">Classification</option>
        <option value="text_to_code">Text-to-Code</option>
        <option value="multilingual">Multilingual</option>
      </select>

      {/* Dataset List */}
      <div className="space-y-3 mb-8">
        {datasets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 bg-white rounded-2xl border shadow-sm text-zinc-500">
            <p className="text-lg font-medium">No datasets found</p>
            <p className="text-sm mt-2">
              No {datasetType.toUpperCase()} datasets have been generated yet.
            </p>
          </div>
        ) : (
          datasets.map((file) => (
            <div
              key={file}
              className="flex justify-between items-center p-4 bg-white rounded-xl shadow-sm border"
            >
              <span className="font-medium text-zinc-800">{file}</span>

              <div className="flex gap-3 items-center">
                <button
                  onClick={() => fetchCSV(file)}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition"
                >
                  <Eye size={16} />
                  View
                </button>

                <button
                  onClick={() => openFullScreen(file)}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition"
                >
                  <ExternalLink size={16} />
                  View Fullscreen
                </button>

                <button
                  onClick={() => deleteDataset(file)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 transition"
                >
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white w-[95%] h-[90%] rounded-3xl shadow-2xl p-6 flex flex-col">

            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold">{selectedFile}</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-zinc-500 hover:text-black text-lg"
              >
                ✕
              </button>
            </div>

            {/* AG Grid Container with FIXED HEIGHT */}
            <div
              className="ag-theme-alpine rounded-xl"
              style={{ height: "600px", width: "100%" }}
            >
              <AgGridReact
                rowData={rowData}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
              />
            </div>

          </div>
        </div>
      )}
    </div>
  );
}