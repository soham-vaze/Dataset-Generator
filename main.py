import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List
import uvicorn
import glob

# Import your existing generator functions
# (Assuming they are in separate files)
from generators.sft import generate_instruction_dataset
from generators.nl_sql import generate_nl2sql_dataset
from generators.rag import generate_rag_dataset
from generators.classification import generate_classification_dataset
from generators.code import generate_code_dataset
from generators.multilingual import generate_multilingual_dataset
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi import Query



app = FastAPI(title="Dataset Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_PATH = "/home/soham/dataset_generator/datasets"
BASE_DATASET_DIR = "datasets"



# =====================================================
# Utility: Create Folder If Not Exists
# =====================================================

def ensure_directory(path: str):
    os.makedirs(path, exist_ok=True)


def get_output_path(dataset_type: str, output_name: str):
    folder = os.path.join(BASE_PATH, dataset_type)
    ensure_directory(folder)
    return os.path.join(folder, f"{output_name}.csv")


# =====================================================
# 1️⃣ SFT Instruction Dataset
# =====================================================

@app.post("/generate/sft")
def sft_dataset(
    topic: str = Form(...),
    model: str = Form(...),
    style: str = Form(...),
    num_pairs: int = Form(...),
    language: str = Form(...),
    temperature: float = Form(...),
    output_name: str = Form(...)
):

    output_path = get_output_path("sft", output_name)

    generate_instruction_dataset(
        topic=topic,
        output_csv_path=output_path,
        models=[model],
        style=style,
        num_pairs=num_pairs,
        language=language,
        temperature=temperature
    )

    return {"message": "SFT dataset generated successfully."}


# =====================================================
# 2️⃣ NL → SQL Dataset
# =====================================================

@app.post("/generate/nl_sql")
async def nl_sql_dataset(
    schema_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...)
):

    schema_path = f"/tmp/{schema_file.filename}"

    with open(schema_path, "wb") as buffer:
        shutil.copyfileobj(schema_file.file, buffer)

    output_path = get_output_path("nl_sql", output_name)

    generate_nl2sql_dataset(
        schema_path=schema_path,
        output_path=output_path,
        model=model,
        num_samples=num_samples
    )

    return {"message": "NL-SQL dataset generated successfully."}


# =====================================================
# 3️⃣ RAG-QA Dataset
# =====================================================

@app.post("/generate/rag_qa")
async def rag_dataset(
    context_file: UploadFile = File(...),
    output_name: str = Form(...),
    model: str = Form(...),
    difficulty: str = Form(...),
    num_pairs: int = Form(...)
):

    file_path = f"/tmp/{context_file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(context_file.file, buffer)

    # Handle txt or pdf
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            document_text = f.read()
    elif file_path.endswith(".pdf"):
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        document_text = ""
        for page in reader.pages:
            document_text += page.extract_text() + "\n"
    else:
        return JSONResponse(content={"error": "Unsupported file format"}, status_code=400)

    output_path = get_output_path("rag_qa", output_name)

    generate_rag_dataset(
        document_text=document_text,
        output_path=output_path,
        model=model,
        difficulty=difficulty,
        max_pairs=num_pairs
    )

    return {"message": "RAG-QA dataset generated successfully."}


# =====================================================
# 4️⃣ Classification Dataset
# =====================================================

@app.post("/generate/classification")
def classification_dataset(
    task_description: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...)
):

    output_path = get_output_path("classification", output_name)

    # For now using fixed 50 samples
    generate_classification_dataset(
        task_description=task_description,
        class_labels=["class1", "class2"],  # can be improved later
        output_path=output_path,
        model=model,
        num_samples=num_samples
    )

    return {"message": "Classification dataset generated successfully."}


# =====================================================
# 5️⃣ Text → Code Dataset
# =====================================================

@app.post("/generate/text_to_code")
def text_to_code_dataset(
    domain: str = Form(...),
    programming_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    num_samples: int = Form(...),
    temperature: float = Form(...)
):

    output_path = get_output_path("text_to_code", output_name)

    generate_code_dataset(
        domain=domain,
        programming_language=programming_language,
        output_path=output_path,
        model=model,
        num_samples=num_samples,
        temperature=temperature
    )

    return {"message": "Text-to-Code dataset generated successfully."}


# =====================================================
# 6️⃣ Multilingual Dataset
# =====================================================

@app.post("/generate/multilingual")
def multilingual_dataset(
    topic: str = Form(...),
    source_language: str = Form(...),
    destination_language: str = Form(...),
    output_name: str = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    num_samples: int = Form(...)
):

    output_path = get_output_path("multilingual", output_name)

    generate_multilingual_dataset(
        topic=topic,
        source_language=source_language,
        target_language=destination_language,
        output_path=output_path,
        model=model,
        num_samples=num_samples,
        temperature=temperature
    )

    return {"message": "Multilingual dataset generated successfully."}


# =====================================================
# 7️⃣ View All Generated Datasets (.csv only)
# =====================================================

@app.get("/datasets")
def list_datasets(dataset_type: str = Query(...)):
    folder = Path(BASE_DATASET_DIR) / dataset_type

    if not folder.exists():
        return {"datasets": []}

    csv_files = [f.name for f in folder.glob("*.csv")]

    return {"datasets": csv_files}
@app.get("/datasets/{dataset_type}")
def list_datasets(dataset_type: str):
    folder_path = Path(BASE_DATASET_DIR) / dataset_type

    if not folder_path.exists():
        return {"files": []}

    files = [
        f.name
        for f in folder_path.iterdir()
        if f.suffix == ".csv"
    ]

    return {"files": files}


@app.get("/datasets/{dataset_type}/{filename}")
def get_dataset(dataset_type: str, filename: str):
    file_path = Path(BASE_DATASET_DIR) / dataset_type / filename

    if not file_path.exists():
        return {"error": "File not found"}

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename,
    )

@app.get("/datasets/{dataset_type}/{filename}")
def get_dataset(dataset_type: str, filename: str):
    file_path = Path(BASE_DATASET_DIR) / dataset_type / filename

    if not file_path.exists():
        return JSONResponse(content={"error": "File not found"}, status_code=404)

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename,
    )

@app.delete("/datasets/{dataset_type}/{filename}")
def delete_dataset(dataset_type: str, filename: str):
    file_path = Path(BASE_DATASET_DIR) / dataset_type / filename

    if not file_path.exists():
        return JSONResponse(content={"error": "File not found"}, status_code=404)

    os.remove(file_path)

    return {"message": "Dataset deleted successfully"}


# =====================================================
# Run Server
# =====================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
