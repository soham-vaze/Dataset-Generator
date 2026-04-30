# 🐍 Python Production Code Review

**Project:** Dataset Generator (FastAPI Backend)
**Date:** 2026-04-30
**Reviewer:** Senior Python Engineer — Zero-Tolerance Production Review

---

## 1. 📁 File-wise Review

---

### File: `database.py`

**Line 6:** 🔐❌ **CRITICAL — Hardcoded database credentials in source code**

```python
DATABASE_URL = "postgresql://dataset_user:strongpassword@localhost/dataset_db"
```

👉 **Suggested Fix:**
```python
import os

DATABASE_URL: str = os.environ["DATABASE_URL"]
# Or use pydantic-settings:
# from pydantic_settings import BaseSettings
# class Settings(BaseSettings):
#     database_url: str
#     class Config:
#         env_file = ".env"
```

**Line 5:** ⚠️ **Unused import — `Depends` from FastAPI imported but never used**

👉 **Suggested Fix:** Remove `from fastapi import Depends`.

**Line 8:** ⚠️ **No connection pool tuning — will use defaults; no pool_pre_ping for connection health**

👉 **Suggested Fix:**
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
```

**Line 14:** ⚠️ **`declarative_base()` is deprecated in SQLAlchemy 2.0+**

👉 **Suggested Fix:**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**Lines 1-23:** ❌ **No type hints on `get_db()` generator return**

👉 **Suggested Fix:**
```python
from typing import Generator

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### File: `models.py`

**Line 11:** ⚠️ **Column name `format` shadows Python builtin**

👉 **Recommendation:** Rename to `file_format` or `output_format`.

**Lines 1-24:** ⚠️ **No relationship between `User` and `Dataset`**

👉 **Suggested Fix:**
```python
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    # ... existing columns ...
    datasets = relationship("Dataset", back_populates="owner")

class Dataset(Base):
    __tablename__ = "datasets"
    # ... existing columns ...
    owner = relationship("User", back_populates="datasets")
```

**Lines 15-24:** ⚠️ **No index on `user_id` or `dataset_type` — queries filtering by these will be slow at scale**

👉 **Suggested Fix:**
```python
from sqlalchemy import Index

user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
dataset_type = Column(String, nullable=False, index=True)
```

**Lines 1-24:** ⚠️ **No `__repr__` methods — debugging will be painful**

👉 **Suggested Fix:**
```python
def __repr__(self) -> str:
    return f"<User(id={self.id}, email={self.email})>"
```

---

### File: `auth.py`

**Line 10:** 🔐❌ **CRITICAL — Hardcoded JWT secret key**

```python
SECRET_KEY = "supersecretkey"   # change later
```

This is a **showstopper**. Anyone with the source code can forge valid JWTs.

👉 **Suggested Fix:**
```python
import os

SECRET_KEY: str = os.environ["JWT_SECRET_KEY"]
```

**Line 11-12:** ⚠️ **Hardcoded algorithm and token expiry — should be configurable**

👉 **Suggested Fix:**
```python
ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
```

**Line 17-19:** ❌ **Missing return type hint on `hash_password`**

```python
def hash_password(password: str):
```

👉 **Suggested Fix:**
```python
def hash_password(password: str) -> str:
```

**Line 22-24:** ❌ **Missing type hints on `verify_password` parameters and return**

```python
def verify_password(plain_password, hashed_password):
```

👉 **Suggested Fix:**
```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
```

**Line 27-30:** ❌ **Missing return type hint on `create_access_token`**

👉 **Suggested Fix:**
```python
def create_access_token(data: dict) -> str:
```

**Line 29:** ⚠️ **`datetime.utcnow()` is deprecated since Python 3.12**

👉 **Suggested Fix:**
```python
from datetime import datetime, timedelta, timezone

expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
```

**Line 33:** ❌ **Missing return type hint on `get_current_user`**

👉 **Suggested Fix:**
```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
```

**Lines 1-51:** ❌ **No logging — silent authentication failures with no audit trail**

👉 **Recommendation:** Add structured logging for login attempts, token generation, and auth failures.

---

### File: `database_init.py`

**Lines 1-5:** ⚠️ **No error handling or logging — if migration fails, no feedback**

👉 **Suggested Fix:**
```python
import logging

logger = logging.getLogger(__name__)

from database import engine
from models import Base

def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

if __name__ == "__main__":
    init_db()
```

---

### File: `main.py`

**Line 29-33:** 🔐❌ **CRITICAL — CORS allows ALL origins**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` with `allow_credentials=True` is a security anti-pattern. Browsers will reject this combination, but it signals a misconfigured security posture.

👉 **Suggested Fix:**
```python
import os

ALLOWED_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Line 40:** ⚠️ **Hardcoded storage path**

```python
BASE_STORAGE_DIR = Path("local_storage")
```

👉 **Suggested Fix:**
```python
BASE_STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "local_storage"))
```

**Line 48-61:** ❌ **`save_dataset_metadata` — no return type, no error handling around `db.commit()`**

👉 **Suggested Fix:**
```python
def save_dataset_metadata(
    db: Session,
    dataset_id: UUID,
    name: str,
    dataset_type: str,
    format: str,
    storage_key: str,
    user_id: UUID,
) -> None:
    new_dataset = Dataset(
        id=dataset_id, name=name, dataset_type=dataset_type,
        format=format, storage_key=storage_key, status="ready", user_id=user_id,
    )
    db.add(new_dataset)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
```

**Lines 67-92:** ❌ **`sft_dataset` — synchronous endpoint doing blocking I/O (HTTP calls to LLM)**

The generator functions make synchronous `requests.post()` calls. This blocks the event loop thread in FastAPI and will degrade performance under load.

👉 **Suggested Fix:** Either:
1. Run the generator in a thread pool: `await asyncio.to_thread(generate_instruction_dataset, ...)`
2. Or make the generators async with `httpx.AsyncClient`

**Lines 67-92:** ❌ **No try/except — if generation fails, user gets a 500 with no useful message**

👉 **Suggested Fix:**
```python
try:
    generate_instruction_dataset(...)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Dataset generation failed: {str(e)}")
```

**Lines 67-92:** ⚠️ **No response model — undocumented API response schema**

👉 **Suggested Fix:**
```python
from pydantic import BaseModel

class DatasetResponse(BaseModel):
    message: str
    dataset_id: str

@app.post("/generate/sft", response_model=DatasetResponse)
```

**Line 110:** 🔐❌ **CRITICAL — Path traversal vulnerability in file upload**

```python
schema_path = f"/tmp/{schema_file.filename}"
```

An attacker can craft `filename` as `../../etc/passwd` or `..\\..\\windows\\system32\\config` to write files anywhere on the filesystem.

👉 **Suggested Fix:**
```python
import tempfile
from pathlib import PurePosixPath

safe_filename = PurePosixPath(schema_file.filename).name  # strip directory components
if not safe_filename:
    raise HTTPException(status_code=400, detail="Invalid filename")

with tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe_filename).suffix) as tmp:
    shutil.copyfileobj(schema_file.file, tmp)
    schema_path = tmp.name
```

**Line 140:** 🔐❌ **CRITICAL — Same path traversal vulnerability with `context_file.filename`**

```python
file_path = f"/tmp/{context_file.filename}"
```

👉 **Suggested Fix:** Same as above — sanitize filename and use `tempfile`.

**Line 98-126:** ❌ **Mixed async/sync — `async def nl_sql_dataset` but calls synchronous `generate_nl2sql_dataset`**

Using `async def` with blocking code starves the async event loop.

👉 **Suggested Fix:** Either use `def` (FastAPI runs it in threadpool automatically) or wrap in `asyncio.to_thread()`.

**Line 131-170:** ❌ **Same async/sync mismatch in `rag_dataset`**

👉 **Same fix as above.**

**Line 150:** ⚠️ **Import inside function body — `import PyPDF2`**

👉 **Recommendation:** Move to top-level imports.

**Line 189:** ❌ **Hardcoded class labels `["class1", "class2"]` — user cannot specify labels**

```python
generate_classification_dataset(
    ...
    class_labels=["class1", "class2"],
    ...
)
```

👉 **Suggested Fix:** Accept `class_labels` as a Form parameter:
```python
class_labels: str = Form(...)  # comma-separated
# Then:
labels = [l.strip() for l in class_labels.split(",")]
```

**Line 371-381:** ⚠️ **`/register` — no email format validation, no password strength enforcement**

👉 **Suggested Fix:**
```python
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

**Line 399:** ⚠️ **`reload=True` in production server — should be development only**

👉 **Suggested Fix:**
```python
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=os.environ.get("DEBUG", "false").lower() == "true")
```

**Lines 1-399:** ❌ **No global exception handler**

👉 **Suggested Fix:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**Lines 1-399:** ❌ **No logging — entire application uses no `logging` module**

👉 **Recommendation:** Configure structured logging at app startup.

**Lines 1-399:** ❌ **Architecture violation — business logic, routes, and data access all in one file**

👉 **Recommendation:** Separate into:
- `routers/` — API route definitions
- `services/` — business logic
- `repositories/` — database access
- `schemas/` — Pydantic models

**Lines 1-399:** 🔁 **DRY violation — every endpoint repeats the same 5-line pattern:**
```python
dataset_id = uuid.uuid4()
storage_key = f"type/{dataset_id}.csv"
output_path = get_storage_path(storage_key)
output_path.parent.mkdir(parents=True, exist_ok=True)
# ... generate ...
save_dataset_metadata(db, dataset_id, output_name, type, "csv", storage_key, current_user.id)
```

👉 **Suggested Fix:** Extract into a reusable helper or decorator:
```python
def create_dataset_context(dataset_type: str) -> tuple[UUID, Path]:
    dataset_id = uuid.uuid4()
    storage_key = f"{dataset_type}/{dataset_id}.csv"
    output_path = get_storage_path(storage_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return dataset_id, storage_key, output_path
```

---

### File: `generators/sft.py`

**Line 16:** 🔐❌ **Hardcoded internal API URL**

```python
SLM_API = "http://10.30.1.34:11434/api/generate"
```

👉 **Suggested Fix:**
```python
import os
SLM_API: str = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
```

**Lines 36-37:** ⚠️ **Commented-out code — dead code in production**

```python
# response.raise_for_status()
# return response.json()["response"]
```

👉 **Recommendation:** Remove commented-out code.

**Lines 65, 72:** ❌ **Bare `except:` clauses — swallows all exceptions including `SystemExit`, `KeyboardInterrupt`**

```python
try:
    return json.loads(text)
except:
    pass
```

👉 **Suggested Fix:**
```python
except (json.JSONDecodeError, ValueError):
    pass
```

**Lines 115-232:** ❌ **Uses `print()` everywhere — 20+ print statements, no `logging`**

👉 **Suggested Fix:** Replace all `print()` with proper logging:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Generating dataset for topic: %s", topic)
```

**Line 139:** ⚠️ **`datetime.utcnow()` is deprecated in Python 3.12+**

👉 **Suggested Fix:** `datetime.now(timezone.utc).isoformat()`

**Lines 22-55:** ❌ **`call_remote_slm` — no return type hints, no timeout configuration**

👉 **Suggested Fix:**
```python
def call_remote_slm(prompt: str, model: str, temperature: float = 0.7) -> str:
```

**Line 107:** ❌ **`save_dataset` — no error handling if file write fails**

👉 **Recommendation:** Wrap I/O in try/except with proper error propagation.

---

### File: `generators/nl_sql.py`

**Line 13:** 🔐❌ **Hardcoded internal API URL**

👉 **Same fix as `sft.py`.**

**Lines 112-127:** ❌ **`validate_columns` always returns `True` — dead validation logic**

The function iterates over tokens but never returns `False`. The validation is entirely non-functional.

```python
def validate_columns(sql_query: str, column_map: Dict) -> bool:
    # ... token iteration that does nothing ...
    return True  # ALWAYS True
```

👉 **Suggested Fix:**
```python
def validate_columns(sql_query: str, column_map: Dict[str, List[str]]) -> bool:
    sql_keywords = {
        "SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "ON",
        "GROUP", "BY", "ORDER", "HAVING", "COUNT", "SUM", "AVG",
        "MIN", "MAX", "LIMIT", "AS", "INNER", "LEFT", "RIGHT",
        "INSERT", "UPDATE", "DELETE", "INTO", "VALUES", "SET",
        "NOT", "NULL", "IN", "BETWEEN", "LIKE", "IS", "EXISTS",
        "DISTINCT", "DESC", "ASC", "UNION", "ALL", "CREATE", "TABLE",
    }
    tokens = re.findall(r"\b[a-zA-Z_]+\b", sql_query)
    valid_columns = {col for cols in column_map.values() for col in cols}
    valid_tables = set(column_map.keys())

    for token in tokens:
        if token.upper() in sql_keywords:
            continue
        if token in valid_tables or token in valid_columns:
            continue
        return False  # Unknown token — likely hallucinated column

    return True
```

**Line 133-145:** ❌ **`validate_execution` — bare `except Exception` with silent failure**

👉 **Suggested Fix:**
```python
except sqlite3.Error as e:
    logger.warning("SQL validation failed: %s", e)
    return False
```

**Line 133-145:** ⚠️ **SQLite connection not closed on exception path**

👉 **Suggested Fix:** Use `with` context manager:
```python
with sqlite3.connect(":memory:") as conn:
    cursor = conn.cursor()
    for ddl in ddl_statements:
        cursor.execute(ddl)
    cursor.execute(sql_query)
    return True
```

**Lines 15-28:** ❌ **`query_model` — missing return type hint**

👉 **Suggested Fix:**
```python
def query_model(prompt: str, model: str) -> str:
```

**Lines 1-210:** ❌ **Uses `print()` everywhere — no `logging`**

---

### File: `generators/rag.py`

**Line 9:** ⚠️ **`nltk.download("punkt")` at module import — downloads data on every process start**

👉 **Suggested Fix:** Guard with check or move to setup script:
```python
import nltk
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)
```

**Line 16:** 🔐❌ **Hardcoded internal API URL**

👉 **Same fix as other generators.**

**Lines 33-37:** ⚠️ **Commented-out code**

```python
# response.raise_for_status()
# return response.json()["response"]
```

👉 **Recommendation:** Remove.

**Lines 119-120:** ❌ **Bare `except:` clause in `extract_json_array`**

```python
except:
    pass
```

👉 **Suggested Fix:** `except (json.JSONDecodeError, ValueError):`

**Lines 140-142:** ❌ **Bare `except:` fallback in `generate_qa_batch`**

```python
except:
    raw_output = re.sub(r"```json|```", "", raw_output)
    qa_list = json.loads(raw_output)
```

👉 **Suggested Fix:** Catch specific exceptions.

**Line 155:** ⚠️ **Printing raw LLM output to stdout — may contain sensitive data from user documents**

```python
print(raw_output[:1000])
```

👉 **Recommendation:** Remove or use `logger.debug()` with appropriate log level.

**Lines 1-450:** ❌ **Uses `print()` everywhere — no `logging`**

**Lines 1-450:** 🔁 **`call_remote_slm` and `save_dataset` are duplicated from `sft.py`**

👉 **Recommendation:** Extract into shared `generators/utils.py` module.

---

### File: `generators/classification.py`

**Line 10:** 🔐❌ **Hardcoded internal API URL**

👉 **Same fix as other generators.**

**Lines 141-147:** ❌ **`raw_output` referenced in `except` block but may be unbound**

```python
try:
    raw_output = query_model(prompt, model, temperature)
    data = extract_json(raw_output)
    df = pd.DataFrame(data["samples"])
except Exception as e:
    print("⚠️ Failed to parse model output:", e)
    print("Model output was:\n", raw_output)  # ← UnboundLocalError if query_model() fails
    continue
```

👉 **Suggested Fix:**
```python
raw_output = ""
try:
    raw_output = query_model(prompt, model, temperature)
    data = extract_json(raw_output)
    df = pd.DataFrame(data["samples"])
except Exception as e:
    logger.warning("Failed to parse model output: %s", e)
    if raw_output:
        logger.debug("Model output: %s", raw_output[:500])
    continue
```

**Lines 1-180:** ❌ **Uses `print()` everywhere — no `logging`**

**Lines 1-180:** 🔁 **`save_dataset`, `extract_json`, `query_model` duplicated from other generators**

---

### File: `generators/code.py`

**Line 15:** 🔐❌ **Hardcoded internal API URL**

👉 **Same fix.**

**Lines 62-73:** ❌ **Bare `except:` clauses in `extract_json`**

👉 **Suggested Fix:** `except (json.JSONDecodeError, ValueError):`

**Line 164-170:** ❌ **`response_text` referenced in `except` block — may be unbound**

```python
try:
    response_text = query_model(prompt, model, temperature)
    data = extract_json(response_text)
except Exception as e:
    print(response_text[:1000])  # ← UnboundLocalError
    continue
```

👉 **Suggested Fix:** Initialize `response_text = ""` before `try`.

**Lines 1-220:** ❌ **Uses `print()` everywhere — no `logging`**

**Lines 1-220:** 🔁 **`save_dataset`, `extract_json`, `query_model`, `normalize_text` duplicated**

---

### File: `generators/multilingual.py`

**Line 12:** 🔐❌ **Hardcoded internal API URL**

👉 **Same fix.**

**Line 210-212:** ⚠️ **`import re` inside function body — should be at top of file**

```python
import re
sentences = re.split(r'\n+|(?<=[.!?])\s+', content)
```

👉 **Suggested Fix:** Move `import re` to top of file. (Note: `re` is already imported at top of other generator files but NOT in this file's top-level imports.)

**Lines 47-51:** ❌ **`query_model` missing return type hint**

👉 **Suggested Fix:**
```python
def query_model(prompt: str, model: str) -> str:
```

**Line 115:** ❌ **`get_language_code` missing return type hint**

👉 **Suggested Fix:**
```python
def get_language_code(lang_name: str) -> str:
```

**Lines 1-300:** ❌ **Mixed `print()` and `logging` — inconsistent logging strategy**

The file imports `logging` and creates a logger on line 11 (`ml = logging.getLogger("multilingual")`) but never uses it — all output goes through `print()`.

👉 **Suggested Fix:** Use the logger everywhere instead of `print()`.

**Lines 1-300:** 🔁 **`save_dataset` and `query_model` duplicated from other generators**

---

### File: `generators/dataset.py`

**Line 8:** 🔐❌ **Hardcoded internal API URL**

```python
SLM_API = "http://10.30.1.34:11434/api/generate"
```

**Line 9:** ❌ **Hardcoded output file path**

```python
OUTPUT_JSONL = "/home/soham/dataset_generator/datasets/qa_finetuning_v2.jsonl"
```

This is a **developer's local path** committed to source code.

👉 **Suggested Fix:** Accept as CLI argument or environment variable.

**Line 97:** ❌ **`exit(1)` used instead of raising an exception**

```python
if not success:
    exit(1)
```

👉 **Suggested Fix:**
```python
if not success:
    raise RuntimeError(f"Failed to generate valid data after {max_retries} retries")
```

**Lines 28-31:** ❌ **Bare `except:` clause in `extract_json`**

👉 **Suggested Fix:** `except (json.JSONDecodeError, ValueError):`

**Lines 1-110:** ❌ **Uses `print()` everywhere — no `logging`**

**Lines 1-110:** ❌ **No type hints on function parameters (`epic`, `feature`, `story`, `model`, `num_batches`)**

👉 **Suggested Fix:**
```python
def generate_qa_dataset(epic: str, feature: str, story: str, model: str, num_batches: int) -> None:
```

---

### File: `generators/dataset2.py`

**Lines 1-130:** 🔁❌ **CRITICAL DRY VIOLATION — This file is a near-exact copy of `generators/dataset.py`**

The ONLY differences between `dataset.py` and `dataset2.py` are:
- Line 9: Output path (`qa_finetuning_v2.jsonl` vs `qa_finetuning_v3.jsonl`)

This is a textbook DRY violation.

👉 **Suggested Fix:** Delete `dataset2.py`. Parameterize the output path in `dataset.py`:
```python
def generate_qa_dataset(epic: str, feature: str, story: str, model: str, num_batches: int, output_path: str) -> None:
```

**All other issues from `dataset.py` apply identically here.**

---

### File: `generators/automate_gen.py`

**Line 4-6:** ❌ **Hardcoded file paths and script references**

```python
REQUIREMENTS_FILE = "requirements.json"
GENERATOR_SCRIPT = "dataset.py"
MODEL = "llama3.1:8b"
```

👉 **Suggested Fix:**
```python
import os

REQUIREMENTS_FILE: str = os.environ.get("REQUIREMENTS_FILE", "requirements.json")
GENERATOR_SCRIPT: str = os.environ.get("GENERATOR_SCRIPT", "dataset.py")
MODEL: str = os.environ.get("MODEL", "llama3.1:8b")
```

**Lines 1-45:** ❌ **No type hints on `run_automation` or any variables**

👉 **Suggested Fix:**
```python
def run_automation() -> None:
```

**Lines 1-45:** ❌ **Uses `print()` everywhere — no `logging`**

**Lines 1-45:** ⚠️ **`subprocess.run(command, check=True)` — no timeout set**

If the child process hangs, the automation hangs forever.

👉 **Suggested Fix:**
```python
subprocess.run(command, check=True, timeout=600)
```

---

### File: `generators/automate_gen2.py`

**Lines 1-45:** 🔁❌ **CRITICAL DRY VIOLATION — This file is a near-exact copy of `generators/automate_gen.py`**

The ONLY differences:
- Line 4: `REQUIREMENTS_FILE = "req2.json"` vs `"requirements.json"`
- Line 5: `GENERATOR_SCRIPT = "dataset2.py"` vs `"dataset.py"`

👉 **Suggested Fix:** Delete `automate_gen2.py`. Parameterize `automate_gen.py` via CLI args:
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", default="requirements.json")
    parser.add_argument("--generator", default="dataset.py")
    parser.add_argument("--model", default="llama3.1:8b")
    args = parser.parse_args()
    run_automation(args.requirements, args.generator, args.model)
```

---

## 2. 🚨 Critical Issues (Must Fix Before Merge)

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🔐 Security | `auth.py` | 10 | **Hardcoded JWT secret key** — anyone can forge tokens |
| 2 | 🔐 Security | `database.py` | 6 | **Hardcoded database credentials** in source code |
| 3 | 🔐 Security | `main.py` | 29 | **CORS allows all origins** with credentials enabled |
| 4 | 🔐 Security | `main.py` | 110 | **Path traversal** in NL-SQL file upload (`schema_file.filename`) |
| 5 | 🔐 Security | `main.py` | 140 | **Path traversal** in RAG file upload (`context_file.filename`) |
| 6 | 🔐 Security | All generators | Various | **Hardcoded internal IP** `10.30.1.34` in 7 files |
| 7 | Bug | `generators/nl_sql.py` | 112-127 | **`validate_columns` always returns True** — validation is dead code |
| 8 | Bug | `generators/classification.py` | 147 | **`raw_output` unbound** in except block → `UnboundLocalError` |
| 9 | Bug | `generators/code.py` | 167 | **`response_text` unbound** in except block → `UnboundLocalError` |
| 10 | ⚡ Perf | `main.py` | 98,131 | **Blocking sync calls inside `async def`** endpoints — starves event loop |
| 11 | Arch | `main.py` | 189 | **Hardcoded class labels** `["class1", "class2"]` — feature is broken for users |
| 12 | 🔐 Security | `main.py` | 371 | **No email validation or password strength requirements** on registration |

---

## 3. ⚠️ Improvements (Should Fix)

| # | Category | File(s) | Issue |
|---|----------|---------|-------|
| 1 | Architecture | `main.py` | Monolithic file — routes, business logic, and DB access all in one |
| 2 | Logging | All files | `print()` used everywhere — no structured `logging` |
| 3 | Type Safety | All files | Missing type hints on most function signatures and return types |
| 4 | Exception Handling | All generators | Bare `except:` and `except Exception` clauses |
| 5 | API Design | `main.py` | No Pydantic request/response schemas |
| 6 | API Design | `main.py` | No API versioning (`/api/v1/...`) |
| 7 | DB | `models.py` | No indexes on `user_id`, `dataset_type`; no relationships |
| 8 | DB | `database.py` | Deprecated `declarative_base()`; no pool tuning |
| 9 | Config | `main.py` | Hardcoded `BASE_STORAGE_DIR`, `reload=True` |
| 10 | Deprecation | `auth.py`, generators | `datetime.utcnow()` deprecated in Python 3.12+ |
| 11 | Code Smell | `generators/rag.py` | `nltk.download()` at module import time |
| 12 | Code Smell | `generators/multilingual.py` | `import re` inside function body |
| 13 | Code Smell | `generators/multilingual.py` | Logger created but never used |
| 14 | Security | `main.py` | No rate limiting on `/login` or `/register` |
| 15 | Security | `auth.py` | No token refresh or revocation mechanism |

---

## 4. 💡 Best Practice Suggestions

### 4.1 Extract Shared Generator Utilities
Create `generators/utils.py`:
```python
"""Shared utilities for all dataset generators."""
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

def get_api_url() -> str:
    return os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")

def call_model(prompt: str, model: str, temperature: float = 0.7, timeout: int = 180) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}}
    response = requests.post(get_api_url(), json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if "response" not in data:
        raise ValueError(f"Invalid response format: {data}")
    return data["response"]

def extract_json(text: str) -> Dict[str, Any]:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    matches = re.findall(r"\{[\s\S]*\}", text)
    for match in reversed(matches):
        try:
            return json.loads(match)
        except (json.JSONDecodeError, ValueError):
            continue
    raise ValueError(f"JSON parsing failed: {text[:500]}")

def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())

def save_to_csv_and_jsonl(rows: List[Dict[str, Any]], output_path: str) -> None:
    df = pd.DataFrame(rows)
    file_exists = os.path.isfile(output_path)
    df.to_csv(output_path, mode="a", index=False, header=not file_exists)
    jsonl_path = output_path.replace(".csv", ".jsonl")
    df.to_json(jsonl_path, orient="records", lines=True, mode="a")
```

This eliminates duplication across **7 files**.

### 4.2 Configuration Management
Create a `config.py` with `pydantic-settings`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    storage_dir: str = "local_storage"
    ollama_api_url: str = "http://localhost:11434/api/generate"

    class Config:
        env_file = ".env"

settings = Settings()
```

### 4.3 Global Exception Handler
```python
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

### 4.4 Add Health Check
```python
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

### 4.5 Testing Foundation
No tests exist. At minimum:
- Unit tests for `auth.py` (hash, verify, token)
- Unit tests for each generator's `extract_json`, `normalize_text`, quality filters
- Integration tests for API endpoints using `TestClient`
- Mock external LLM calls

---

## 5. 📊 Summary

| Category | Score |
|----------|-------|
| Naming Conventions | **70/100** — mostly snake_case, but inconsistent variable naming; `format` shadows builtin |
| Architecture | **20/100** — monolithic `main.py`, no separation of concerns, no service/repository layers |
| Type Safety | **15/100** — type hints missing on majority of functions; not mypy-compatible |
| Logging | **5/100** — `print()` used everywhere; one file creates a logger but never uses it |
| Exception Handling | **15/100** — bare `except:` clauses, silent failures, no custom exceptions, no global handler |
| Async/Await | **20/100** — blocking sync calls inside `async def`; inconsistent sync/async mixing |
| API Design | **30/100** — no Pydantic schemas, no response models, no versioning, broken class_labels |
| Validation | **20/100** — no email validation, no password policy, path traversal vulns, dead validation code |
| Security | **10/100** — hardcoded secrets, hardcoded DB creds, CORS `*`, path traversal, no rate limiting |
| DRY | **15/100** — massive duplication: `dataset.py`≈`dataset2.py`, `automate_gen.py`≈`automate_gen2.py`, utility functions copied across 7 files |
| Performance | **35/100** — blocking I/O in async endpoints; no caching; `nltk.download()` on every import |
| Configuration | **10/100** — hardcoded URLs, paths, secrets, credentials in 9+ files |
| Testing | **0/100** — zero tests exist |
| **Overall Python Code Quality** | **19/100** |

---

## Final Verdict

# ❌ Not Ready for Production

### Justification:

1. **Security is catastrophic**: Hardcoded JWT secret, hardcoded database password, path traversal vulnerabilities in file uploads, CORS wide open. Any one of these is a blocker.

2. **Zero test coverage**: No unit tests, no integration tests, no test infrastructure.

3. **Architecture is monolithic**: All routes, business logic, and data access in a single file with no separation of concerns.

4. **Massive code duplication**: Two pairs of near-identical files (`dataset.py`/`dataset2.py`, `automate_gen.py`/`automate_gen2.py`), and utility functions (`call_model`, `extract_json`, `save_dataset`, `normalize_text`) copy-pasted across 7 generator files.

5. **No logging infrastructure**: The entire application uses `print()` statements — unacceptable for production observability.

6. **Critical bugs**: `validate_columns` is dead code (always returns `True`), `UnboundLocalError` in two generators' exception handlers, hardcoded class labels make classification endpoint non-functional.

7. **No configuration management**: Internal IP addresses, file paths, and credentials scattered across source files instead of environment variables.

### Minimum requirements before production:
- [ ] Move ALL secrets/credentials to environment variables
- [ ] Fix path traversal vulnerabilities in file uploads
- [ ] Restrict CORS origins
- [ ] Fix `validate_columns` dead code
- [ ] Fix `UnboundLocalError` bugs in classification.py and code.py
- [ ] Extract shared utilities to eliminate duplication
- [ ] Delete duplicate files (`dataset2.py`, `automate_gen2.py`)
- [ ] Replace all `print()` with `logging`
- [ ] Add type hints to all functions
- [ ] Add Pydantic request/response schemas
- [ ] Add global exception handler
- [ ] Add unit and integration tests (minimum 80% coverage)
- [ ] Separate `main.py` into routers, services, and repositories
