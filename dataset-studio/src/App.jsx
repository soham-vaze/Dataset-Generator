import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Datasets from "./pages/Datasets";

export default function App() {
  const [selectedDataset, setSelectedDataset] = useState("sft");
  const [activePage, setActivePage] = useState("generate");

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-indigo-50 via-white to-zinc-100">
      <Sidebar
        selectedDataset={selectedDataset}
        setSelectedDataset={setSelectedDataset}
        activePage={activePage}
        setActivePage={setActivePage}
      />

      <div className="flex-1 p-8">
        {activePage === "generate" ? (
          <Dashboard selectedDataset={selectedDataset} />
        ) : (
          <Datasets />
        )}
      </div>
    </div>
  );
}