export const datasetConfigs = {
  // =====================================================
  // 1️⃣ SFT Instruction Dataset
  // =====================================================
  sft: {
    label: "SFT (Instruction Tuning)",
    endpoint: "/generate/sft",
    fields: [
      { name: "topic", label: "Topic", type: "text" },
      { name: "model", label: "Model", type: "text" },
      {
        name: "style",
        label: "Style",
        type: "select",
        options: ["highly friendly", "begineer friendly", "problem-solving oriented","conversational"],
      },
      { name: "num_pairs", label: "Number of Pairs", type: "number" },
      { name: "language", label: "Language", type: "text" },
      { name: "temperature", label: "Temperature", type: "number", step: "0.1" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

  // =====================================================
  // 2️⃣ NL → SQL Dataset
  // =====================================================
  nl_sql: {
    label: "NL → SQL",
    endpoint: "/generate/nl_sql",
    fields: [
      { name: "schema_file", label: "Schema File (.json)", type: "file" },
      { name: "model", label: "Model", type: "text" },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

  // =====================================================
  // 3️⃣ RAG-QA Dataset
  // =====================================================
  rag_qa: {
    label: "RAG-QA",
    endpoint: "/generate/rag_qa",
    fields: [
      { name: "context_file", label: "Context File (.txt / .pdf)", type: "file" },
      { name: "model", label: "Model", type: "text" },
      {
        name: "difficulty",
        label: "Difficulty",
        type: "select",
        options: ["easy", "medium", "hard"],
      },
      { name: "num_pairs", label: "Number of QA Pairs", type: "number" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

  // =====================================================
  // 4️⃣ Classification Dataset
  // =====================================================
  classification: {
    label: "Classification",
    endpoint: "/generate/classification",
    fields: [
      {
        name: "task_description",
        label: "Task Description",
        type: "textarea",
      },
      { name: "model", label: "Model", type: "text" },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

  // =====================================================
  // 5️⃣ Text → Code Dataset
  // =====================================================
  text_to_code: {
    label: "Text → Code",
    endpoint: "/generate/text_to_code",
    fields: [
      { name: "domain", label: "Domain", type: "text" },
      {
        name: "programming_language",
        label: "Programming Language",
        type: "text",
      },
      { name: "model", label: "Model", type: "text" },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "temperature", label: "Temperature", type: "number", step: "0.1" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

  // =====================================================
  // 6️⃣ Multilingual Dataset
  // =====================================================
  // =====================================================
// 6️⃣ Multilingual Dataset
// =====================================================
  multilingual: {
    label: "Multilingual",
    endpoint: "/generate/multilingual",
    fields: [
      { name: "topic", label: "Topic", type: "text" },

      {
        name: "source_language",
        label: "Source Language",
        type: "select",
        options: [
          "Arabic",
          "Azerbaijani",
          "Basque",
          "Catalan",
          "Chinese",
          "Czech",
          "Danish",
          "Dutch",
          "English",
          "Esperanto",
          "Finnish",
          "French",
          "Galician",
          "German",
          "Greek",
          "Hebrew",
          "Hindi",
          "Hungarian",
          "Indonesian",
          "Irish",
          "Italian",
          "Japanese",
          "Kyrgyz",
          "Korean",
          "Malay",
          "Persian",
          "Polish",
          "Portuguese",
          "Portuguese (Brazil)",
          "Russian",
          "Slovak",
          "Spanish",
          "Swedish",
          "Turkish",
          "Ukrainian",
          "Urdu"
        ],
      },

      {
        name: "destination_language",
        label: "Target Language",
        type: "select",
        options: [
          "Arabic",
          "Azerbaijani",
          "Basque",
          "Catalan",
          "Chinese",
          "Czech",
          "Danish",
          "Dutch",
          "English",
          "Esperanto",
          "Finnish",
          "French",
          "Galician",
          "German",
          "Greek",
          "Hebrew",
          "Hindi",
          "Hungarian",
          "Indonesian",
          "Irish",
          "Italian",
          "Japanese",
          "Kyrgyz",
          "Korean",
          "Malay",
          "Persian",
          "Polish",
          "Portuguese",
          "Portuguese (Brazil)",
          "Russian",
          "Slovak",
          "Spanish",
          "Swedish",
          "Turkish",
          "Ukrainian",
          "Urdu"
        ],
      },

      { name: "model", label: "Generation Model", type: "text" },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "temperature", label: "Temperature", type: "number", step: "0.1" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },
};