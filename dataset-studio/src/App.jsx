import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import Dashboard from "./pages/Dashboard";
import Datasets from "./pages/Datasets";
import DatasetViewer from "./pages/DatasetViewer";
import Pipeline from "./pages/Pipeline";
import Login from "./pages/Login";
import Register from "./pages/Register";
import { useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import AnimatedBackground from "./components/AnimatedBackground";

function AppLayout({ children, onSelectDataset }) {
  return (
    <div className="flex min-h-screen bg-dark relative">
      <AnimatedBackground />
      <div className="dot-grid fixed inset-0 z-0 pointer-events-none" />
      <Sidebar onSelectDataset={onSelectDataset} />
      <div className="flex-1 flex flex-col relative z-10">
        <Header />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="flex-1 overflow-y-auto p-6 md:p-8"
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}

function App() {
  const { isAuthenticated } = useAuth();
  const [selectedDataset, setSelectedDataset] = useState(null);

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  return (
    <Routes>
      {/* Fullscreen viewer — no sidebar/header */}
      <Route path="/view-dataset/:datasetId" element={<DatasetViewer />} />

      <Route
        path="/"
        element={
          <AppLayout onSelectDataset={setSelectedDataset}>
            <Dashboard selectedDataset={selectedDataset} onSelectDataset={setSelectedDataset} />
          </AppLayout>
        }
      />
      <Route
        path="/pipeline"
        element={
          <AppLayout onSelectDataset={setSelectedDataset}>
            <Pipeline />
          </AppLayout>
        }
      />
      <Route
        path="/datasets"
        element={
          <AppLayout onSelectDataset={setSelectedDataset}>
            <Datasets />
          </AppLayout>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default App;
