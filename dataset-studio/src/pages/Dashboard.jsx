import { useState } from "react";
// Ensure languageMapping is exported from your config file
import { datasetConfigs, languageMapping } from "../config/datasetConfigs";
import { useNotification } from "../context/NotificationContext";
import { useAuth } from "../context/AuthContext";
import { usePendingJobs } from "../context/PendingJobsContext";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export default function Dashboard({ selectedDataset, onSelectDataset }) {
  const config = datasetConfigs[selectedDataset];
  const { addNotification } = useNotification();
  const { token } = useAuth();
  const { addJob, resolveJob } = usePendingJobs();

  const [formData, setFormData] = useState({});
  const [message, setMessage] = useState(null);

  // If nothing selected
  if (!config) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="bg-white rounded-3xl shadow-lg px-12 py-10 border border-zinc-100 text-center">
          <h2 className="text-2xl font-semibold text-zinc-900">
            Please select a dataset type
          </h2>
          <p className="text-zinc-500 mt-3">
            Choose a dataset category from the left sidebar to begin generation.
          </p>
        </div>
      </div>
    );
  }

  /* =========================
       FORM HANDLING
  ========================== */

  const handleChange = (e, field) => {
    const value = field.type === "file" ? e.target.files[0] : e.target.value;

    if (field.name === "source_language") {
      // RESET target language if the source changes to prevent invalid pairs
      setFormData((prev) => ({
        ...prev,
        [field.name]: value,
        destination_language: "", 
      }));
    } else {
      setFormData((prev) => ({ 
        ...prev, 
        [field.name]: value 
      }));
    }
  };

  const handleSubmit = () => {
    const form = new FormData();
    const datasetName = formData["output_name"] || "your dataset";
    const jobId = crypto.randomUUID();

    config.fields.forEach((field) => {
      if (field.name === "num_pairs" || field.name === "num_samples") {
        form.append(field.name, Number(formData[field.name]));
      } else {
        form.append(field.name, formData[field.name]);
      }
    });

    // Register job as pending immediately
    addJob(jobId, datasetName, selectedDataset);

    // Show submitted message and reset form immediately — don't block the UI
    setMessage({
      type: "info",
      text: "Your request has been submitted. You are free to submit another request.",
    });
    setFormData({});

    // Fire request in background; notify user when done
    fetch(`${API_BASE}${config.endpoint}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
      .then(async (res) => {
        let data;
        try {
          data = await res.json();
        } catch {
          data = { detail: `Server returned ${res.status} with no body` };
        }
        return { ok: res.ok, data };
      })
      .then(({ ok, data }) => {
        if (ok) {
          resolveJob(jobId, true);
          addNotification(
            `🎉 Your dataset "${datasetName}" has been successfully created!`,
            "success"
          );
        } else {
          resolveJob(jobId, false, data.detail || "Unknown error");
          addNotification(
            `Dataset "${datasetName}" failed: ${data.detail || "Unknown error"}`,
            "error"
          );
        }
      })
      .catch((err) => {
        resolveJob(jobId, false, err.message);
        addNotification(
          `Dataset "${datasetName}" failed: ${err.message}`,
          "error"
        );
      });
  };

  /* =========================
         GENERATION FORM
  ========================== */

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      {/* Back Button */}
      <button
        onClick={() => onSelectDataset(null)}
        className="mb-6 text-sm text-indigo-600 hover:underline"
      >
        ← Back to Dataset Types
      </button>

      {/* Header */}
      <div className="mb-10">
        <h2 className="text-3xl font-bold text-zinc-900">
          {config.label} Dataset Generator
        </h2>
        <p className="text-zinc-500 mt-2 text-sm">
          Configure parameters and generate structured training datasets.
        </p>
      </div>

      {/* Card */}
      <div className="bg-white rounded-3xl shadow-2xl p-10 border border-zinc-100 transition-all">
        <div className="space-y-6">
          {config.fields.map((field) => {
            
            // --- DYNAMIC LOGIC FOR MULTILINGUAL TARGETS ---
            let currentOptions = field.options || [];
            
            if (field.name === "destination_language") {
              const selectedSource = formData["source_language"];
              // Filter options based on mapping, or empty if no source selected
              currentOptions = selectedSource ? (languageMapping[selectedSource] || []) : [];
            }

            return (
              <div key={field.name}>
                <label className="block text-sm font-medium text-zinc-700 mb-2">
                  {field.label}
                </label>

                {field.type === "textarea" ? (
                  <textarea
                    rows="4"
                    value={formData[field.name] || ""}
                    className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none transition"
                    onChange={(e) => handleChange(e, field)}
                  />
                ) : field.type === "select" ? (
                  <select
                    className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none transition"
                    value={formData[field.name] || ""}
                    onChange={(e) => handleChange(e, field)}
                  >
                    <option value="">
                      {field.name === "destination_language" && !formData["source_language"] 
                        ? "Select source language first" 
                        : "Select option"}
                    </option>
                    {currentOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    step={field.step}
                    value={field.type === "file" ? undefined : (formData[field.name] || "")}
                    className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none transition"
                    onChange={(e) => handleChange(e, field)}
                  />
                )}
              </div>
            );
          })}

          {/* Status Message */}
          {message && (
            <div
              className={`p-4 rounded-xl text-sm ${
                message.type === "success"
                  ? "bg-green-100 text-green-700"
                  : message.type === "info"
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Button */}
          <button
            onClick={handleSubmit}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-2xl transition-all duration-300 shadow-md hover:shadow-lg flex items-center justify-center"
          >
            Generate Dataset
          </button>
        </div>
      </div>
    </div>
  );
}   