import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { datasetConfigs, languageMapping } from "../config/datasetConfigs";
import { useNotification } from "../context/NotificationContext";
import { useAuth } from "../context/AuthContext";
import { usePendingJobs } from "../context/PendingJobsContext";
import CategoryCard from "../components/CategoryCard";
import GlassCard from "../components/GlassCard";
import { categoryMeta } from "../components/CategoryCard";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export default function Dashboard({ selectedDataset, onSelectDataset }) {
  const config = datasetConfigs[selectedDataset];
  const { addNotification } = useNotification();
  const { token } = useAuth();
  const { addJob, resolveJob } = usePendingJobs();

  const [formData, setFormData] = useState({});
  const [message, setMessage] = useState(null);

  // ===== NO DATASET SELECTED — SHOW CATEGORY GRID =====
  if (!config) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Hero section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-12 text-center"
        >
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">
            <span className="text-zinc-100">What would you like to </span>
            <span className="text-gradient">generate</span>
            <span className="text-zinc-100"> today?</span>
          </h1>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Choose a dataset type to start building production-ready training data
          </p>
        </motion.div>

        {/* Category grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
          {Object.keys(datasetConfigs).map((key, index) => (
            <CategoryCard
              key={key}
              configKey={key}
              label={datasetConfigs[key].label}
              onClick={() => onSelectDataset(key)}
              index={index}
            />
          ))}
        </div>

        {/* Quick tips */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-12 text-center"
        >
          <p className="text-xs text-zinc-600">
            💡 Tip: You can submit multiple generation requests simultaneously — they run in the background.
          </p>
        </motion.div>
      </div>
    );
  }

  // ===== DATASET SELECTED — SHOW GENERATION FORM =====

  const meta = categoryMeta[selectedDataset] || {};

  const handleChange = (e, field) => {
    const value = field.type === "file" ? e.target.files[0] : e.target.value;

    if (field.name === "source_language") {
      setFormData((prev) => ({
        ...prev,
        [field.name]: value,
        destination_language: "",
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [field.name]: value,
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

    addJob(jobId, datasetName, selectedDataset);

    setMessage({
      type: "info",
      text: "Your request has been submitted. You are free to submit another request.",
    });
    setFormData({});

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

  // Group fields into logical steps
  const configFields = config.fields.filter((f) => f.name !== "output_name");
  const outputField = config.fields.find((f) => f.name === "output_name");

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <AnimatePresence mode="wait">
        <motion.div
          key={selectedDataset}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ duration: 0.4 }}
        >
          {/* Back button */}
          <motion.button
            onClick={() => onSelectDataset(null)}
            whileHover={{ x: -3 }}
            className="group flex items-center gap-2 mb-8 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back to generators
          </motion.button>

          {/* Header with icon */}
          <div className="flex items-start gap-4 mb-8">
            <div className={`${meta.accentColor || "text-zinc-400"} ${meta.bgAccent || "bg-white/5"} p-3 rounded-2xl`}>
              <div className="w-8 h-8">
                {meta.icon}
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-zinc-100 tracking-tight">
                {config.label}
              </h2>
              <p className="text-zinc-500 mt-1 text-sm">
                {meta.description || "Configure parameters and generate structured training datasets."}
              </p>
            </div>
          </div>

          {/* Form card */}
          <GlassCard hover={false} className="p-8">
            <div className="space-y-6">
              {/* Main fields */}
              {configFields.map((field, index) => {
                let currentOptions = field.options || [];

                if (field.name === "destination_language") {
                  const selectedSource = formData["source_language"];
                  currentOptions = selectedSource ? (languageMapping[selectedSource] || []) : [];
                }

                return (
                  <motion.div
                    key={field.name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <label className="block text-xs font-medium text-zinc-400 mb-2 tracking-wide uppercase">
                      {field.label}
                    </label>

                    {field.type === "textarea" ? (
                      <textarea
                        rows="4"
                        value={formData[field.name] || ""}
                        className="glass-input w-full resize-none"
                        placeholder={`Enter ${field.label.toLowerCase()}...`}
                        onChange={(e) => handleChange(e, field)}
                      />
                    ) : field.type === "select" ? (
                      <select
                        className="glass-select w-full"
                        value={formData[field.name] || ""}
                        onChange={(e) => handleChange(e, field)}
                      >
                        <option value="">
                          {field.name === "destination_language" && !formData["source_language"]
                            ? "Select source language first"
                            : `Select ${field.label.toLowerCase()}`}
                        </option>
                        {currentOptions.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : field.type === "file" ? (
                      <div className="relative">
                        <input
                          type="file"
                          className="glass-input w-full file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-primary/20 file:text-primary-300 hover:file:bg-primary/30 file:cursor-pointer file:transition-colors"
                          onChange={(e) => handleChange(e, field)}
                        />
                      </div>
                    ) : field.type === "number" ? (
                      <input
                        type="number"
                        step={field.step}
                        value={formData[field.name] || ""}
                        className="glass-input w-full"
                        placeholder={field.step ? "0.7" : "100"}
                        onChange={(e) => handleChange(e, field)}
                      />
                    ) : (
                      <input
                        type="text"
                        value={formData[field.name] || ""}
                        className="glass-input w-full"
                        placeholder={`Enter ${field.label.toLowerCase()}...`}
                        onChange={(e) => handleChange(e, field)}
                      />
                    )}

                    {/* Helper hints */}
                    {field.name === "temperature" && (
                      <p className="text-[11px] text-zinc-600 mt-1.5 ml-1">
                        Lower values (0.1-0.3) = more focused. Higher values (0.7-1.0) = more creative.
                      </p>
                    )}
                    {field.name === "num_pairs" && (
                      <p className="text-[11px] text-zinc-600 mt-1.5 ml-1">
                        Recommended: 50-200 pairs for fine-tuning experiments.
                      </p>
                    )}
                    {field.name === "num_samples" && (
                      <p className="text-[11px] text-zinc-600 mt-1.5 ml-1">
                        Recommended: 50-500 samples depending on your use case.
                      </p>
                    )}
                  </motion.div>
                );
              })}

              {/* Divider */}
              <div className="h-px bg-white/[0.04] my-2" />

              {/* Output name */}
              {outputField && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: configFields.length * 0.05 }}
                >
                  <label className="block text-xs font-medium text-zinc-400 mb-2 tracking-wide uppercase">
                    {outputField.label}
                  </label>
                  <input
                    type="text"
                    value={formData[outputField.name] || ""}
                    className="glass-input w-full"
                    placeholder="my-dataset-v1"
                    onChange={(e) => handleChange(e, outputField)}
                  />
                  <p className="text-[11px] text-zinc-600 mt-1.5 ml-1">
                    This will be used as the filename for your generated dataset.
                  </p>
                </motion.div>
              )}

              {/* Status message */}
              <AnimatePresence>
                {message && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    className={`p-4 rounded-xl text-sm border ${
                      message.type === "success"
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        : message.type === "info"
                        ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
                        : "bg-red-500/10 text-red-300 border-red-500/20"
                    }`}
                  >
                    {message.text}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit button */}
              <motion.button
                onClick={handleSubmit}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
                <span>Generate Dataset</span>
              </motion.button>
            </div>
          </GlassCard>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
