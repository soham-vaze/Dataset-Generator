import { useState } from "react";
import { datasetConfigs } from "../config/datasetConfigs";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export default function Dashboard({ selectedDataset }) {
  const config = datasetConfigs[selectedDataset];

  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  if (!config) {
    return <div>Select a dataset type.</div>;
  }

  const handleChange = (e, field) => {
    if (field.type === "file") {
      setFormData({ ...formData, [field.name]: e.target.files[0] });
    } else {
      setFormData({ ...formData, [field.name]: e.target.value });
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const form = new FormData();

      config.fields.forEach((field) => {
        if (!formData[field.name]) {
          throw new Error(`${field.label} is required`);
        }

        if (field.name === "num_pairs") {
          form.append(field.name, Number(formData[field.name]));
        } else {
          form.append(field.name, formData[field.name]);
        }
      });

      const response = await fetch(
        `${API_BASE}${config.endpoint}`,
        {
          method: "POST",
          body: form,
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Backend error");
      }

      setMessage({
        type: "success",
        text: result.message,
      });

    } catch (error) {
      setMessage({
        type: "error",
        text: error.message,
      });
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="max-w-4xl mx-auto">

      {/* Header */}
      <div className="mb-10">
        <h2 className="text-3xl font-bold text-zinc-900 tracking-tight">
          {config.label} Dataset Generator
        </h2>
        <p className="text-zinc-500 mt-2 text-sm">
          Configure parameters and generate structured training datasets.
        </p>
      </div>

      {/* Card */}
      <div className="backdrop-blur-xl bg-white/70 border border-white/40 rounded-3xl shadow-xl p-10">

        <div className="space-y-6">
          {config.fields.map((field) => (
            <div key={field.name}>
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                {field.label}
              </label>

              {field.type === "textarea" ? (
                <textarea
                  rows="4"
                  className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none"
                  onChange={(e) => handleChange(e, field)}
                />
              ) : field.type === "select" ? (
                <select
                  className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none"
                  onChange={(e) => handleChange(e, field)}
                >
                  {field.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type}
                  step={field.step}
                  className="w-full border border-zinc-200 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none"
                  onChange={(e) => handleChange(e, field)}
                />
              )}
            </div>
          ))}

          {/* Status Message */}
          {message && (
            <div
              className={`p-4 rounded-xl text-sm ${
                message.type === "success"
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Button */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-2xl transition-all duration-300 shadow-md hover:shadow-lg disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Dataset"}
          </button>
        </div>
      </div>
    </div>
  );
}