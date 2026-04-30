import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { NotificationProvider } from "./context/NotificationContext";
import { PendingJobsProvider } from "./context/PendingJobsContext";
import Toast from "./components/Toast";

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <AuthProvider>
      <PendingJobsProvider>
        <NotificationProvider>
          <App />
          <Toast />
        </NotificationProvider>
      </PendingJobsProvider>
    </AuthProvider>
  </BrowserRouter>
);