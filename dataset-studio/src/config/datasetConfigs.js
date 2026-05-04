const supportedLanguages = [
  "Albanian", "Arabic", "Azerbaijani", "Basque", "Bengali", "Bulgarian", 
  "Catalan", "Chinese", "Chinese (traditional)", "Czech", "Danish", 
  "Dutch", "English", "Esperanto", "Estonian", "Finnish", "French", 
  "Galician", "German", "Greek", "Hebrew", "Hindi", "Hungarian", 
  "Indonesian", "Irish", "Italian", "Japanese", "Korean", "Kyrgyz", 
  "Latvian", "Lithuanian", "Malay", "Norwegian", "Persian", "Polish", 
  "Portuguese", "Portuguese (Brazil)", "Romanian", "Russian", "Slovak", 
  "Slovenian", "Spanish", "Swedish", "Tagalog", "Thai", "Turkish", 
  "Ukrainian", "Urdu", "Vietnamese"
];

export const languageMapping = {
  "Portuguese": ["English", "Spanish"],
  "Spanish": ["English", "Portuguese"],
  "English": supportedLanguages.filter(l => l !== "English"),
  // Default for all others: they can only go to English
  ...supportedLanguages.reduce((acc, lang) => {
    if (!["English", "Spanish", "Portuguese"].includes(lang)) {
      acc[lang] = ["English"];
    }
    return acc;
  }, {})
};


export const datasetConfigs = {
  // =====================================================
  // 1️⃣ SFT Instruction Dataset
  // =====================================================
  sft: {
    label: "SFT (Instruction Tuning)",
    endpoint: "/generate/sft",
    fields: [
      { name: "topic", label: "Topic", type: "text" },
      { name: "model", label: "Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","qwen2.5:7b","gemma3:1b"]
       },
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
      { name: "model", label: "Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","llama3.2:3b","qwen2.5:7b"]
       },
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
      { name: "model", label: "Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","llama3.2:3b","qwen2.5:7b"]
       },
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
      { name: "model", label: "Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","qwen2.5:7b","gemma3:1b"]
       },
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
      { name: "model", label: "Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","llama3.2:3b","qwen2.5:7b"]
       },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "temperature", label: "Temperature", type: "number", step: "0.1" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },

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
        options: supportedLanguages, // Use the variable
      },
      {
        name: "destination_language",
        label: "Target Language",
        type: "select",
        options: [], // Leave empty, Dashboard will populate this
      },
      { name: "model", label: "Generation Model", type: "select",
        options: ["llama3.1:8b","gemma3:4b","llama3.2:3b","qwen2.5:7b"]
       },
      { name: "num_samples", label: "Number of Samples", type: "number" },
      { name: "temperature", label: "Temperature", type: "number", step: "0.1" },
      { name: "output_name", label: "Output Name", type: "text" },
    ],
  },
};