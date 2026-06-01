import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { datasetConfigs, languageMapping } from "../config/datasetConfigs";
import { useNotification } from "../context/NotificationContext";
import { useAuth } from "../context/AuthContext";
import { usePendingJobs } from "../context/PendingJobsContext";
import CategoryCard from "../components/CategoryCard";
import GlassCard from "../components/GlassCard";
import TagInput from "../components/TagInput";
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
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Hero section */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="mb-14 text-center"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/[0.06] border border-primary/[0.1] mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
            <span className="text-[11px] font-semibold text-primary-300 tracking-wide uppercase">AI-Powered Generation</span>
          </div>

          <h1 className="text-4xl md:text-[3.2rem] font-extrabold tracking-[-0.03em] mb-5 leading-[1.1]">
            <span className="text-zinc-100">What would you like to </span>
            <span className="text-gradient">generate</span>
            <span className="text-zinc-100"> today?</span>
          </h1>
          <p className="text-zinc-500 text-base md:text-lg max-w-xl mx-auto leading-relaxed">
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

        {/* Tip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-14 flex justify-center"
        >
          <div className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-white/[0.015] border border-white/[0.04]">
            <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
            </svg>
            <p className="text-[12px] text-zinc-600">
              You can submit multiple generation requests simultaneously — they run in the background.
            </p>
          </div>
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
        // Reset target language selection whenever source changes
        destination_language: [],
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
      if (field.name === "num_pairs" || field.name === "num_samples" || field.name === "num_samples_per_pair") {
        form.append(field.name, Number(formData[field.name]));
      } else if (field.type === "tags") {
        const tags = formData[field.name] || [];
        form.append(field.name, tags.join(","));
      } else if (field.type === "multiselect") {
        // Serialize selected languages as a comma-separated string
        const selected = formData[field.name] || [];
        form.append(field.name, selected.join(","));
      } else {
        form.append(field.name, formData[field.name] ?? "");
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
            `Your dataset "${datasetName}" has been successfully created!`,
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

  const configFields = config.fields.filter((f) => f.name !== "output_name");
  const outputField = config.fields.find((f) => f.name === "output_name");

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <AnimatePresence mode="wait">
        <motion.div
          key={selectedDataset}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          {/* Back button */}
          <motion.button
            onClick={() => onSelectDataset(null)}
            whileHover={{ x: -3 }}
            className="group flex items-center gap-2 mb-8 text-sm text-zinc-600 hover:text-zinc-300 transition-colors duration-200"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back to generators
          </motion.button>

          {/* Header with icon */}
          <div className="flex items-start gap-4 mb-8">
            <div className={`${meta.accentColor || "text-zinc-400"} ${meta.bgAccent || "bg-white/5"} p-3 rounded-2xl border border-white/[0.06]`}>
              <div className="w-8 h-8">
                {meta.icon}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-zinc-100 tracking-[-0.02em]">
                  {config.label}
                </h2>
                <span className={`text-[10px] font-semibold uppercase tracking-[0.1em] px-2.5 py-1 rounded-lg ${meta.bgAccent} ${meta.accentColor}`}>
                  {meta.tag}
                </span>
              </div>
              <p className="text-zinc-500 mt-1.5 text-sm leading-relaxed">
                {meta.description || "Configure parameters and generate structured training datasets."}
              </p>
            </div>
          </div>

          {/* Form card */}
          <GlassCard hover={false} className="p-8 relative overflow-hidden">
            {/* Top accent */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

            <div className="space-y-6">
              {/* Main fields */}
              {configFields.map((field, index) => {
                let currentOptions = field.options || [];

                if (field.name === "destination_language") {
                  const selectedSource = formData["source_language"];
                  currentOptions = selectedSource ? (languageMapping[selectedSource] || []) : [];
                }
                // For multiselect, currentOptions is already set above (same logic)

                return (
                  <motion.div
                    key={field.name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04, ease: [0.25, 0.46, 0.45, 0.94] }}
                    className="space-y-2"
                  >
                    <label className="block text-[11px] font-semibold text-zinc-500 tracking-[0.08em] uppercase">
                      {field.label}
                    </label>

                    {field.type === "textarea" ? (
                      <textarea
                        rows="4"
                        value={formData[field.name] || ""}
                        className="glass-input w-full resize-none"
                        placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}...`}
                        onChange={(e) => handleChange(e, field)}
                      />
                    ) : field.type === "tags" ? (
                      <TagInput
                        tags={formData[field.name] || []}
                        onChange={(newTags) =>
                          setFormData((prev) => ({ ...prev, [field.name]: newTags }))
                        }
                      />
                    ) : field.type === "multiselect" ? (
                      // Multi-select rendered as a scrollable checkbox list
                      <div>
                        {!formData["source_language"] ? (
                          <div className="glass-input w-full py-3 px-4 text-sm text-zinc-500">
                            Select source language first
                          </div>
                        ) : currentOptions.length === 0 ? (
                          <div className="glass-input w-full py-3 px-4 text-sm text-zinc-500">
                            No target languages available for this source
                          </div>
                        ) : (
                          <div className="glass-input w-full max-h-52 overflow-y-auto p-2 space-y-0.5">
                            {currentOptions.map((opt) => {
                              const selected = (formData[field.name] || []).includes(opt);
                              return (
                                <label
                                  key={opt}
                                  className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors duration-150 ${
                                    selected
                                      ? "bg-primary/[0.12] text-zinc-200"
                                      : "hover:bg-white/[0.04] text-zinc-400"
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={selected}
                                    onChange={() => {
                                      const current = formData[field.name] || [];
                                      const updated = current.includes(opt)
                                        ? current.filter((l) => l !== opt)
                                        : [...current, opt];
                                      setFormData((prev) => ({ ...prev, [field.name]: updated }));
                                    }}
                                    className="accent-violet-500 w-3.5 h-3.5 shrink-0"
                                  />
                                  <span className="text-sm">{opt}</span>
                                </label>
                              );
                            })}
                          </div>
                        )}
                        {/* Show selected count badge */}
                        {(formData[field.name] || []).length > 0 && (
                          <p className="text-[11px] text-zinc-500 mt-1.5 flex items-center gap-1">
                            <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                            {(formData[field.name] || []).length} language{(formData[field.name] || []).length !== 1 ? "s" : ""} selected:{" "}
                            {(formData[field.name] || []).join(", ")}
                          </p>
                        )}
                      </div>
                    ) : field.type === "select" ? (
                      <select
                        className="glass-select w-full"
                        value={formData[field.name] || ""}
                        onChange={(e) => handleChange(e, field)}
                      >
                        <option value="">
                          {`Select ${field.label.toLowerCase()}`}
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
                          className="glass-input w-full file:mr-4 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-primary/[0.15] file:text-primary-300 hover:file:bg-primary/[0.25] file:cursor-pointer file:transition-all"
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
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Lower values (0.1-0.3) = more focused. Higher values (0.7-1.0) = more creative.
                      </p>
                    )}
                    {field.name === "num_pairs" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Recommended: 50-200 pairs for fine-tuning experiments.
                      </p>
                    )}
                    {field.name === "num_samples" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Recommended: 50-500 samples depending on your use case.
                      </p>
                    )}
                    {field.name === "training_pairs" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Format: Source-Target pairs separated by commas. E.g. English-Hindi, Hindi-English
                      </p>
                    )}
                    {field.name === "zero_shot_pairs" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Evaluation-only pairs that never appear in training. Used to test cross-lingual transfer.
                      </p>
                    )}
                    {field.name === "domains" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Add domains like: daily conversation, navigation, weather, reminders. Leave empty for defaults.
                      </p>
                    )}
                    {field.name === "num_samples_per_pair" && (
                      <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                        <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                        Number of translation samples per language direction. Recommended: 50-200.
                      </p>
                    )}
                    )}
                  </motion.div>
                );
              })}

              {/* Divider */}
              <div className="h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

              {/* Output name */}
              {outputField && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: configFields.length * 0.04 }}
                  className="space-y-2"
                >
                  <label className="block text-[11px] font-semibold text-zinc-500 tracking-[0.08em] uppercase">
                    {outputField.label}
                  </label>
                  <input
                    type="text"
                    value={formData[outputField.name] || ""}
                    className="glass-input w-full"
                    placeholder="my-dataset-v1"
                    onChange={(e) => handleChange(e, outputField)}
                  />
                  <p className="text-[11px] text-zinc-600 flex items-center gap-1.5">
                    <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                    This will be used as the filename for your generated dataset.
                  </p>
                </motion.div>
              )}

              {/* Status message */}
              <AnimatePresence>
                {message && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.98 }}
                    className={`p-4 rounded-xl text-sm border flex items-start gap-3 ${
                      message.type === "success"
                        ? "bg-emerald-500/[0.06] text-emerald-300 border-emerald-500/[0.15]"
                        : message.type === "info"
                        ? "bg-blue-500/[0.06] text-blue-300 border-blue-500/[0.15]"
                        : "bg-red-500/[0.06] text-red-300 border-red-500/[0.15]"
                    }`}
                  >
                    {message.type === "info" && (
                      <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                      </svg>
                    )}
                    <span>{message.text}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit button */}
              <motion.button
                onClick={handleSubmit}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="btn-primary w-full flex items-center justify-center gap-2.5 mt-2"
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
