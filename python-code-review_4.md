# 🔍 Python Code Review — Dataset Generator API

**Reviewer:** Senior Python Engineer (Production-Grade Review)  
**Date:** 2026-05-08  
**Scope:** All Python files — full context review  
**Standard:** Zero-tolerance, production PR standards

---

## 1. 📁 File-wise Review

---

### File: `main.py`

**Line 24:** ⚠️ Module-level side effect during import  
`configure_generators(api_url=settings.ollama_api_url)` is called at import time. If this module is imported by tests or other scripts, this side effect will execute unconditionally.

👉 **Suggested Fix:**
```python
# Move into a startup event or factory function
@app.on_event("startup")
async def startup_event() -> None:
    configure_generators(api_url=settings.ollama_api_url)
    init_db()  # Also initialize DB tables on startup
```

**Line 79:** ⚠️ No database initialization on startup  
Tables are never created automatically when the app starts. `database_init.py` exists but is never called from the application entry point.

👉 **Suggested Fix:**
```python
from infrastructure.db.database_init import init_db

@app.on_event("startup")
async def startup_event() -> None:
    configure_generators(api_url=settings.ollama_api_url)
    init_db()
```

**Line 47:** ⚠️ `allow_methods` is restrictive — missing `PUT`, `PATCH`, `OPTIONS`  
While minimal, if the API evolves, this will silently break new endpoints. Acceptable for now but should be documented.

👉 **Recommendation:** Add a comment explaining why only `GET`, `POST`, `DELETE` are allowed, or use `["*"]` if not security-critical.

**Line 78:** ⚠️ No `lifespan` context manager used  
`@app.on_event("startup")` is deprecated in newer FastAPI versions. Use the `lifespan` parameter instead.

👉 **Suggested Fix:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_generators(api_url=settings.ollama_api_url)
    init_db()
    yield

app = FastAPI(title="Dataset Generator API", lifespan=lifespan)
```

---

### File: `infrastructure/config/settings.py`

**Line 13:** 🔐❌ **CRITICAL — Hardcoded database credentials**  
`database_url: str = "postgresql://postgres:admin123@localhost/dataset_db"` contains a hardcoded password (`admin123`). This is a severe security vulnerability if committed to version control.

👉 **Suggested Fix:**
```python
database_url: str = "postgresql://postgres:changeme@localhost/dataset_db"
# OR better: no default at all, force env var
# database_url: str  # Required — must be set via env
```

**Line 16:** 🔐❌ **CRITICAL — Hardcoded JWT secret key**  
`jwt_secret_key: str = "change-this-to-a-secure-random-key"` is a known-insecure default. If `.env` is not configured, the application runs with a trivially guessable secret, allowing token forgery.

👉 **Suggested Fix:**
```python
import secrets

class Settings(BaseSettings):
    jwt_secret_key: str  # No default — force configuration
    # OR at minimum:
    # jwt_secret_key: str = secrets.token_urlsafe(64)
```

**Line 22:** ⚠️ CORS origins default is development-only  
`cors_origins: List[str] = ["http://localhost:5173"]` — in production this should be explicitly configured. Consider raising an error or warning if `debug=False` and the default is still active.

👉 **Recommendation:**
```python
@field_validator("cors_origins")
@classmethod
def validate_cors(cls, v: List[str], info) -> List[str]:
    # Log warning if using default in non-debug mode
    return v
```

**Line 28:** ⚠️ Hardcoded Ollama API URL  
`ollama_api_url: str = "http://10.30.1.34:11434/api/generate"` contains a hardcoded internal IP address. This will fail in any environment other than the original development network.

👉 **Suggested Fix:**
```python
ollama_api_url: str = "http://localhost:11434/api/generate"
```

---

### File: `infrastructure/db/database.py`

**Line 9-13:** ⚠️ Missing type annotations on module-level variables  

👉 **Suggested Fix:**
```python
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker as SessionMaker

engine: Engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal: SessionMaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
```

**Line 27-31:** 🔁 **DRY Violation** — `get_db()` is duplicated  
This exact function is duplicated in `interfaces/api/dependencies.py` (lines 41-46). Both create a `SessionLocal()` and yield it.

👉 **Suggested Fix:** Remove the duplicate in `dependencies.py` and import from `database.py`, or keep only one canonical location.

---

### File: `infrastructure/db/database_init.py`

No critical issues. Clean implementation.

---

### File: `infrastructure/db/models.py`

**Line 12-23:** ⚠️ Missing `Index` for `email` column  
While `unique=True` creates an implicit unique constraint, an explicit index annotation is clearer for query optimization documentation.

**Line 15:** ⚠️ Missing `String` length constraints  
`Column(String)` without a length limit may cause issues with some DB engines and allows unbounded input.

👉 **Suggested Fix:**
```python
email = Column(String(255), unique=True, nullable=False)
hashed_password = Column(String(255), nullable=False)
```

**Line 33:** ⚠️ Same issue — `name`, `dataset_type`, `format`, `storage_key`, `status` all lack `String` length constraints.

👉 **Suggested Fix:**
```python
name = Column(String(255), nullable=False)
dataset_type = Column(String(50), nullable=False, index=True)
format = Column(String(20), nullable=False)
storage_key = Column(String(500), nullable=False)
status = Column(String(20), default="ready")
```

---

### File: `infrastructure/db/user_repository.py`

**Line 37-46:** ⚠️ `create()` catches bare `Exception`  
While it does `rollback()` and `raise`, catching bare `Exception` is overly broad.

👉 **Suggested Fix:**
```python
from sqlalchemy.exc import SQLAlchemyError

try:
    self._db.commit()
    self._db.refresh(user)
except SQLAlchemyError:
    self._db.rollback()
    raise
```

---

### File: `infrastructure/db/dataset_repository.py`

**Line 56-60:** ⚠️ Same bare `Exception` catch as `user_repository.py`  

👉 **Suggested Fix:** Same as above — catch `SQLAlchemyError` instead.

**Line 67-75:** ⚠️ Same pattern repeated in `delete()`.

🔁 **DRY Violation:** The `create()` method pattern (add → commit → refresh → rollback on error) is duplicated across `user_repository.py` and `dataset_repository.py`. Consider a base repository class.

👉 **Suggested Fix:**
```python
class BaseRepository:
    def __init__(self, db: Session):
        self._db = db

    def _commit(self) -> None:
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
```

---

### File: `domain/entities/dataset.py`

No critical issues. Clean dataclass entity.

---

### File: `domain/entities/user.py`

No critical issues. Clean dataclass entity.

---

### File: `domain/interfaces/dataset_repository.py`

No critical issues. Clean abstract interface.

---

### File: `domain/interfaces/user_repository.py`

No critical issues. Clean abstract interface.

---

### File: `app/services/auth_service.py`

**Line 27:** ⚠️ Truncation of password to 72 bytes  
`password.encode("utf-8")[:72]` — while this is bcrypt's limitation, silently truncating can confuse users. Should be documented or validated upstream.

👉 **Recommendation:** Add a `field_validator` in `RegisterRequest` to reject passwords longer than 72 bytes, or document this behavior.

**Line 42:** ⚠️ `data: dict` — missing type hint for dict values  

👉 **Suggested Fix:**
```python
def create_access_token(self, data: dict[str, str]) -> str:
```

**Line 44-45:** ⚠️ `user_id: str | None` uses Python 3.10+ union syntax  
If supporting Python 3.9, this will fail. Use `Optional[str]` or add `from __future__ import annotations`.

👉 **Suggested Fix:**
```python
user_id: Optional[str] = payload.get("sub")
```

---

### File: `app/services/storage_service.py`

**Line 32:** ⚠️ `filename: str | None` — uses 3.10+ union syntax  
Same issue as `auth_service.py`.

👉 **Suggested Fix:**
```python
def sanitize_filename(filename: Optional[str]) -> str:
```

**Line 38-42:** ⚠️ `save_upload_to_temp` takes `upload_file` with no type hint  

👉 **Suggested Fix:**
```python
from fastapi import UploadFile

@staticmethod
def save_upload_to_temp(upload_file: UploadFile, suffix: str = "") -> str:
```

**Line 21:** ⚠️ Path traversal protection is good, but `ValueError` is raised without logging.

👉 **Recommendation:** Add a security log:
```python
if not resolved.is_relative_to(self._base_dir):
    logger.warning("Path traversal attempt detected: %s", storage_key)
    raise ValueError("Invalid storage key: path traversal detected")
```

---

### File: `app/use_cases/auth.py`

**Line 20:** ⚠️ `ValueError("Email already registered")` — exposes whether an email exists in the system. This is an **account enumeration vulnerability**.

👉 **Suggested Fix:**
```python
# Use a generic message
raise ValueError("Registration failed")
# Or better: use a custom exception
class RegistrationError(Exception): ...
```

**Line 39:** ⚠️ `str | None` — Python 3.10+ syntax, use `Optional[str]`.

---

### File: `app/use_cases/generate_dataset.py`

**Line 21-30:** ⚠️ `extract_document_text()` opens files without size validation  
A malicious user could upload a multi-GB file and exhaust server memory.

👉 **Suggested Fix:**
```python
import os

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def extract_document_text(file_path: str, filename: str) -> str:
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")
    ...
```

**Line 22-29:** ⚠️ File extension check is case-sensitive  
`.TXT` or `.PDF` files would be rejected.

👉 **Suggested Fix:**
```python
lower_name = filename.lower()
if lower_name.endswith(".txt"):
    ...
elif lower_name.endswith(".pdf"):
    ...
```

**Line 35-50:** 🔁 **DRY Violation** — `_save_metadata()` always hardcodes `format="csv"`  
The format should be dynamic, especially since JSONL files are also generated.

👉 **Suggested Fix:**
```python
def _save_metadata(
    dataset_id: UUID,
    user_id: UUID,
    name: str,
    dataset_type: str,
    storage_key: str,
    dataset_repo: DatasetRepositoryInterface,
    format: str = "csv",
) -> None:
    ...
```

**Lines 55-186:** 🔁 **Major DRY Violation** — Six nearly identical `generate_*` functions  
Every function follows the exact same pattern:
1. Create storage context
2. Call generator
3. Save metadata
4. Return dataset ID

👉 **Suggested Fix:** Extract a generic orchestrator:
```python
from typing import Any, Callable, Dict

def _run_generation(
    dataset_type: str,
    output_name: str,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
    generator_fn: Callable[..., None],
    generator_kwargs: Dict[str, Any],
) -> str:
    dataset_id, storage_key, output_path = storage.create_dataset_context(dataset_type)
    generator_kwargs["output_path"] = str(output_path)  # or output_csv_path
    generator_fn(**generator_kwargs)
    _save_metadata(dataset_id, user_id, output_name, dataset_type, storage_key, dataset_repo)
    return str(dataset_id)
```

---

### File: `app/use_cases/manage_dataset.py`

**Line 34-37:** ⚠️ File deletion without error handling  
`file_path.unlink()` can raise `PermissionError` or `OSError` which is not caught.

👉 **Suggested Fix:**
```python
try:
    if file_path.exists():
        file_path.unlink()
except OSError as e:
    logger.error("Failed to delete file %s: %s", file_path, e)
    # Continue with DB deletion anyway
```

---

### File: `interfaces/api/auth_routes.py`

**Line 31-33:** ⚠️ Manual form validation instead of using Pydantic `Body`  
The route accepts `Form(...)` fields and manually creates `RegisterRequest`. This bypasses FastAPI's automatic validation and error formatting.

👉 **Suggested Fix:**
```python
from fastapi import Body

@router.post("/register", response_model=MessageResponse)
def register(
    payload: RegisterRequest = Body(...),
    user_repo: UserRepositoryInterface = Depends(get_user_repo),
) -> dict:
    ...
```

**Line 36:** ⚠️ Catching bare `Exception` for Pydantic validation  
`except Exception as e: raise HTTPException(status_code=400, detail=str(e))` — this could leak internal error messages to the client.

👉 **Suggested Fix:**
```python
from pydantic import ValidationError

try:
    validated = RegisterRequest(email=email, password=password)
except ValidationError as e:
    raise HTTPException(status_code=422, detail=e.errors())
```

**Line 49:** 🔐 ⚠️ Login failure returns 400 instead of 401  
`HTTPException(status_code=400, detail="Incorrect email or password")` — failed authentication should return `401 Unauthorized`.

👉 **Suggested Fix:**
```python
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)
```

---

### File: `interfaces/api/dataset_routes.py`

**Line 26-39:** ⚠️ Missing `response_model` on `list_datasets_route`  
`@router.get("/datasets")` returns an untyped dict. Define a proper response model.

👉 **Suggested Fix:**
```python
from typing import List
from interfaces.schemas.dataset import DatasetListResponse

class DatasetListItem(BaseModel):
    id: str
    name: str
    format: str
    created_at: Optional[datetime]

class DatasetListResponse(BaseModel):
    datasets: List[DatasetListItem]

@router.get("/datasets", response_model=DatasetListResponse)
```

**Line 42-55:** ⚠️ Missing `response_model` on `get_dataset_route`  
Returns `FileResponse` but has no response model annotation.

**Line 53:** ⚠️ Hardcoded `media_type="text/csv"` — format could be JSONL.

👉 **Suggested Fix:**
```python
media_type = "text/csv" if entity.format == "csv" else "application/jsonl"
filename_ext = entity.format
return FileResponse(
    path=file_path,
    media_type=media_type,
    filename=f"{entity.name}.{filename_ext}",
)
```

---

### File: `interfaces/api/generation_routes.py`

**Lines 28-56, 62-100, etc.:** 🔁 **Major DRY Violation** — Six route handlers with identical error-handling boilerplate  
Every handler follows:
```python
try:
    dataset_id = generate_*(...)
except Exception as e:
    logger.error(...)
    raise HTTPException(status_code=500, ...)
return {"message": "...", "dataset_id": dataset_id}
```

👉 **Suggested Fix:** Create a decorator or utility:
```python
from functools import wraps

def handle_generation_errors(generation_type: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error("%s generation failed: %s", generation_type, e)
                raise HTTPException(status_code=500, detail="Dataset generation failed")
        return wrapper
    return decorator
```

**Lines 28-230:** ⚡ **Performance — Synchronous blocking I/O in all route handlers**  
All generation routes are synchronous (`def`, not `async def`) and call blocking LLM APIs (`requests.post`). FastAPI runs sync functions in a threadpool, but with only a few workers, this will block under concurrent load.

👉 **Suggested Fix:** Either:
1. Use `async def` with `httpx.AsyncClient` in generators, OR
2. Use `BackgroundTasks` for long-running generation, OR
3. Use a task queue (Celery/ARQ) for production workloads.

**Line 155:** ⚠️ No input validation on `num_samples`, `temperature`, `num_pairs`  
Users can pass `num_samples=1000000` or `temperature=-5`. No bounds checking anywhere.

👉 **Suggested Fix:**
```python
from pydantic import BaseModel, Field

class SFTRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    model: str = Field(..., min_length=1)
    num_pairs: int = Field(..., ge=1, le=1000)
    temperature: float = Field(..., ge=0.0, le=2.0)
    ...
```

---

### File: `interfaces/api/health_routes.py`

No critical issues. Simple and correct.

---

### File: `interfaces/api/dependencies.py`

**Lines 41-46:** 🔁 **DRY Violation** — `get_db()` duplicated from `infrastructure/db/database.py`  
Exact same function exists in `database.py` lines 27-31.

👉 **Suggested Fix:**
```python
from infrastructure.db.database import get_db
# Remove local get_db() definition
```

**Line 53:** ⚠️ `get_dataset_repo` returns `DatasetRepositoryInterface` — good.

---

### File: `interfaces/schemas/auth.py`

**Line 9-12:** ⚠️ Password validation is minimal  
Only checks `len(v) < 8`. No complexity requirements (uppercase, digit, special char).

👉 **Suggested Fix:**
```python
@field_validator("password")
@classmethod
def validate_password(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    return v
```

---

### File: `interfaces/schemas/dataset.py`

No critical issues. Clean schemas.

---

### File: `generators/utils.py`

**Line 13:** ⚠️ Module-level mutable global state  
`_api_url` is a module-level global mutated by `configure()`. This is thread-unsafe and makes testing difficult.

👉 **Suggested Fix:**
```python
# Use a simple namespace or dataclass to encapsulate config
from dataclasses import dataclass

@dataclass
class _Config:
    api_url: str = "http://localhost:11434/api/generate"

_config = _Config()

def configure(api_url: str) -> None:
    _config.api_url = api_url

def get_api_url() -> str:
    return _config.api_url
```

**Line 46-63:** ⚠️ `call_model()` uses `requests.post()` — blocking HTTP call  
This is a synchronous blocking call. When called from FastAPI async context (even in threadpool), it's suboptimal for high concurrency.

👉 **Recommendation:** Consider `httpx` with async support for future migration.

**Line 53:** 🔐 ⚠️ No request timeout validation  
`timeout` parameter defaults to 180 seconds. An attacker could trigger many simultaneous generation requests to exhaust threadpool workers (slow-loris-style DoS).

👉 **Recommendation:** Add rate limiting middleware to the FastAPI app.

**Line 121-149:** 🔁 **DRY Violation** — `save_dataset()` and `save_dataframe()` are nearly identical  
Both write CSV + JSONL. The only difference is input type (list of dicts vs DataFrame).

👉 **Suggested Fix:**
```python
def save_dataset(rows: List[Dict[str, Any]], output_path: str) -> None:
    df = pd.DataFrame(rows)
    save_dataframe(df, output_path)

def save_dataframe(df: pd.DataFrame, output_path: str) -> None:
    file_exists = os.path.exists(output_path)
    df.to_csv(output_path, mode="a", index=False, header=not file_exists)
    jsonl_path = output_path.replace(".csv", ".jsonl")
    df.to_json(jsonl_path, orient="records", lines=True, mode="a")
```

---

### File: `generators/sft.py`

**Line 150-160:** ⚠️ Hardcoded file path in `__main__` block  
`output_csv_path="/home/soham/dataset_generator/datasets/instr_response_v2.csv"` — hardcoded absolute path from a developer's machine.

👉 **Recommendation:** Use `argparse` or relative paths.

**Line 67-94:** ⚠️ LLM prompt injection risk  
User-supplied `topic`, `language`, and `style` are directly interpolated into the prompt without sanitization. While this is an LLM call (not SQL), prompt injection could cause the model to produce unintended outputs.

👉 **Recommendation:** Add input length limits and sanitization for prompt fields.

**Line 76:** ⚠️ Raw f-string prompt with curly braces  
The JSON format example `{{"pairs": [...]}}` uses double braces for escaping — this is correct but fragile. Consider using a template engine or `.format()` with explicit keys.

---

### File: `generators/nl_sql.py`

**Line 95-100:** 🔐 ⚠️ **SQL injection risk in DDL generation**  
`json_to_sqlite_ddl()` constructs DDL statements by string interpolation:
```python
ddl = f"CREATE TABLE {table_name} ({', '.join(column_defs)});"
```
If `table_name` or column names contain malicious SQL, this could lead to SQL injection in the validation step.

👉 **Suggested Fix:**
```python
import re

def _sanitize_identifier(name: str) -> str:
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name

# Then:
table_name = _sanitize_identifier(table["table_name"])
col_name = _sanitize_identifier(col["name"])
```

**Line 175-176:** ⚠️ Hardcoded paths in `__main__`.

---

### File: `generators/rag.py`

**Line 1-12:** ⚠️ `import ollama` — direct SDK import  
The RAG generator uses `ollama` Python SDK directly for embeddings (line 174-180), while other generators use `generators.utils.call_model()` which goes through HTTP. This is inconsistent.

**Line 16-20:** ⚠️ NLTK downloads at import time  
`nltk.download()` is called at module import. This has network side-effects and can fail silently in air-gapped environments.

👉 **Suggested Fix:**
```python
# Move to a setup/init function, not module import
def _ensure_nltk_data() -> None:
    for resource in ["punkt", "punkt_tab"]:
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)
```

**Line 174-180:** ⚡ **Performance** — Embedding calls are sequential  
Each QA pair requires two embedding calls (answer + context). These could be batched.

**Line 240-243:** ⚠️ Commented-out code left in production  
```python
# if not length_check(answer):
#     logger.debug("Failed length check")
#     continue
```

👉 **Recommendation:** Remove commented-out code or add a configuration flag.

---

### File: `generators/classification.py`

**Line 69:** ⚠️ Logging raw model output at DEBUG level  
`logger.debug("Raw model output: %s", raw_output[:500])` — could log sensitive content if task descriptions contain PII.

**Line 80:** ⚠️ Hardcoded paths in `__main__`.

---

### File: `generators/code.py`

**Line 37:** ⚠️ Quality filter rejects `"pass"` in code  
`if "TODO" in code or "pass" in code` — this would reject valid Python code that legitimately uses `pass` (e.g., abstract method stubs, placeholder classes). This is a **bug**.

👉 **Suggested Fix:**
```python
# Only reject if code is ONLY "pass"
if code.strip() == "pass":
    return False
```

**Line 39-40:** 🔁 **DRY Violation** — `basic_quality_filter()` is nearly identical to `quality_filter()` in `sft.py`  
Both check `len(instruction) < 20` and `len(response/code) < 50/40`.

👉 **Suggested Fix:** Consolidate into `generators/utils.py`:
```python
def quality_filter(instruction: str, content: str, min_instruction_len: int = 20, min_content_len: int = 50) -> bool:
    ...
```

---

### File: `generators/multilingual.py`

**Line 72-82:** ⚠️ `get_translation_model()` auto-downloads packages at runtime  
`package.install_from_path(pkg.download())` downloads and installs packages during a user request. This can take minutes and will timeout the HTTP request.

👉 **Suggested Fix:** Pre-install required language packs at deployment time, or add a separate admin endpoint for package installation.

**Line 73:** ⚠️ Emoji in error messages  
`"❌ No Argos model available for ..."` — emoji in exception messages is unprofessional for production APIs.

👉 **Recommendation:** Remove emoji from error messages.

---

### File: `generators/dataset.py` (QA generator)

**Line 69-82:** ⚠️ `system_content` is constructed inside the loop  
The system content string is the same on every iteration but is redefined inside the loop body. Move it outside.

**Line 74-76:** ⚠️ Non-serializable dict used in JSONL `content` field  
```python
{"role": "user", "content": {"context": {...}, "acceptance_criteria": ...}}
```
The `content` value is a dict, not a string. Some downstream consumers expect `content` to be a string.

👉 **Suggested Fix:**
```python
{"role": "user", "content": json.dumps({"context": {...}, "acceptance_criteria": ...})}
```

---

### File: `generators/automate_gen.py`

**Line 31-39:** 🔐❌ **CRITICAL — `subprocess.run()` with user-controlled arguments**  
```python
command: List[str] = ["python3", generator_script, "--epic", epic, "--feature", feature, "--story", story, ...]
subprocess.run(command, check=True, timeout=600)
```
While arguments are passed as a list (safe from shell injection), the `generator_script` path is user-configurable via CLI. If this module were exposed via API, it could execute arbitrary scripts.

👉 **Recommendation:** Validate `generator_script` is a known, expected path:
```python
ALLOWED_SCRIPTS = {"dataset.py"}
if os.path.basename(generator_script) not in ALLOWED_SCRIPTS:
    raise ValueError(f"Unknown generator script: {generator_script}")
```

**Line 30:** ⚠️ `total_stories = total_stories + 1` — use `+=` operator.

👉 **Suggested Fix:**
```python
total_stories += 1
```

---

### File: `domain/entities/__init__.py`

No critical issues. Proper re-exports with `__all__`.

---

### All `__init__.py` files (empty ones)

No issues. Empty `__init__.py` files are standard.

---

## 2. 🚨 Critical Issues (Must Fix Before Merge)

| # | Category | File | Issue |
|---|----------|------|-------|
| 1 | 🔐 Security | `infrastructure/config/settings.py:13` | Hardcoded database password `admin123` |
| 2 | 🔐 Security | `infrastructure/config/settings.py:16` | Hardcoded JWT secret key — allows token forgery |
| 3 | 🔐 Security | `generators/nl_sql.py:95-100` | SQL injection via unsanitized identifiers in DDL construction |
| 4 | ⚡ Performance | `interfaces/api/generation_routes.py` (all routes) | Synchronous blocking LLM calls in request handlers — will exhaust threadpool under load |
| 5 | ❌ Bug | `generators/code.py:37` | Quality filter rejects valid Python code containing `pass` keyword |
| 6 | 🔐 Security | `app/use_cases/generate_dataset.py:21-30` | No file size validation — DoS via large file upload |
| 7 | 🔐 Security | `interfaces/api/auth_routes.py:49` | Login failure returns 400 instead of 401 |

---

## 3. ⚠️ Improvements (Should Fix)

| # | Category | File | Issue |
|---|----------|------|-------|
| 1 | 🔁 DRY | `app/use_cases/generate_dataset.py` | Six nearly identical `generate_*` functions — extract common orchestrator |
| 2 | 🔁 DRY | `interfaces/api/generation_routes.py` | Six route handlers with identical error-handling boilerplate |
| 3 | 🔁 DRY | `generators/utils.py` | `save_dataset()` and `save_dataframe()` are duplicative |
| 4 | 🔁 DRY | `generators/code.py` + `generators/sft.py` | Duplicate quality filter logic |
| 5 | 🔁 DRY | `interfaces/api/dependencies.py` + `infrastructure/db/database.py` | Duplicate `get_db()` function |
| 6 | Architecture | `generators/rag.py` | Inconsistent: uses `ollama` SDK directly vs HTTP in other generators |
| 7 | Validation | `interfaces/api/generation_routes.py` | No bounds validation on `num_samples`, `temperature`, etc. |
| 8 | Maintainability | `generators/rag.py:240-243` | Commented-out code in production |
| 9 | Security | `app/use_cases/auth.py:20` | Account enumeration via specific error message |
| 10 | Maintainability | `generators/multilingual.py:73` | Emoji characters in error/log messages |
| 11 | API Design | `interfaces/api/dataset_routes.py` | Missing `response_model` on list and download endpoints |
| 12 | Architecture | `interfaces/api/auth_routes.py:31-33` | Manual form-to-Pydantic instead of using `Body()` |
| 13 | Robustness | `app/use_cases/manage_dataset.py:34-37` | File deletion has no error handling |

---

## 4. 💡 Best Practice Suggestions

### Cross-Cutting Improvements

1. **Add Rate Limiting:** No rate limiting exists anywhere. Add `slowapi` or custom middleware to prevent abuse of generation endpoints.

2. **Use Background Tasks / Task Queue:** Long-running LLM generation should use Celery, ARQ, or at minimum `BackgroundTasks` to avoid blocking HTTP workers.

3. **Add Request ID Middleware:** Add a request ID to all log entries for request tracing:
   ```python
   import uuid
   @app.middleware("http")
   async def add_request_id(request: Request, call_next):
       request.state.request_id = str(uuid.uuid4())
       response = await call_next(request)
       response.headers["X-Request-ID"] = request.state.request_id
       return response
   ```

4. **Custom Exception Classes:** Replace `ValueError` with domain-specific exceptions (`DuplicateEmailError`, `DatasetNotFoundError`, etc.) for cleaner error handling.

5. **Add `py.typed` Marker:** If distributing as a package, add a `py.typed` marker for mypy compatibility.

6. **Alembic Migrations:** `alembic` is in `requirements.txt` but no migration files exist. Using `Base.metadata.create_all()` is unsafe for production schema changes.

7. **Health Check Enhancement:** Add DB connectivity check to `/health`:
   ```python
   @router.get("/health")
   def health_check(db: Session = Depends(get_db)) -> dict:
       try:
           db.execute(text("SELECT 1"))
           return {"status": "ok", "database": "connected"}
       except Exception:
           return JSONResponse(status_code=503, content={"status": "unhealthy"})
   ```

8. **OpenAPI Documentation:** Add `summary` and `description` to all route decorators for auto-generated API docs.

9. **Dependency Pinning:** `requirements.txt` has inconsistent pinning — some use `==`, some use `>=,<`. Standardize.

10. **Python Version Compatibility:** Code uses `str | None` (Python 3.10+ syntax) in some places and `Optional[str]` in others. Standardize.

---

## 5. 📊 Summary

| Category | Score |
|----------|-------|
| Naming Conventions | **90/100** — Consistent snake_case/PascalCase. Minor: emoji in identifiers. |
| Architecture | **78/100** — Clean layering (domain → use_cases → routes), but massive DRY violations in generate_dataset.py and generation_routes.py. |
| Type Safety | **65/100** — Type hints present on most functions, but missing on several parameters (`data: dict`, `upload_file`), inconsistent `str | None` vs `Optional[str]`. |
| Logging | **85/100** — Proper `logging` module usage, no `print()`. Minor: potential PII in debug logs. |
| Exception Handling | **60/100** — Bare `except Exception` in multiple places. No custom exception hierarchy. Silent truncation in auth. |
| Async/Await | **40/100** — All routes and generators are synchronous. Blocking HTTP calls (`requests.post`) in request handlers. No async anywhere. |
| API Design | **70/100** — FastAPI used correctly. Missing response models on some endpoints. Login returns wrong HTTP status. |
| Validation | **55/100** — Pydantic used for auth schemas, but generation inputs have zero validation (no bounds on num_samples, temperature, etc.). No file size limits. |
| Security | **45/100** — Hardcoded secrets, SQL injection in DDL, account enumeration, no rate limiting, no file size validation. Path traversal protection is good. |
| DRY | **40/100** — Severe duplication across generators, routes, use cases, and repositories. |
| Performance | **45/100** — All blocking I/O. No caching. Sequential embedding calls. No background task processing. |
| Configuration | **60/100** — pydantic-settings used correctly, but hardcoded sensitive defaults undermine it entirely. |
| Testing | **0/100** — Zero test files exist. No unit tests, no integration tests, no test infrastructure. |
| **Overall Python Code Quality** | **52/100** |

---

## Final Verdict

### ❌ Not Ready for Production

**Justification:**

1. **Zero test coverage** — No tests exist whatsoever. This alone is a merge blocker.
2. **Hardcoded secrets** — Database password and JWT secret key are committed as defaults, creating critical security vulnerabilities.
3. **SQL injection vulnerability** — Unsanitized DDL construction in `nl_sql.py`.
4. **No input validation** — Generation parameters (`num_samples`, `temperature`) are unbounded, enabling resource exhaustion.
5. **Synchronous blocking architecture** — All LLM calls block HTTP workers; system will become unresponsive under any concurrent load.
6. **Severe DRY violations** — Duplicated logic across 6+ files increases maintenance burden and bug surface area.
7. **No rate limiting** — Generation endpoints can be abused to exhaust LLM/compute resources.

**Minimum requirements before production merge:**
- [ ] Remove all hardcoded secrets; enforce env-var configuration
- [ ] Add input validation with bounds on all generation parameters
- [ ] Sanitize SQL identifiers in DDL construction
- [ ] Add file size validation for uploads
- [ ] Add at minimum unit tests for auth, use cases, and repositories (~80% coverage)
- [ ] Implement background task processing for generation endpoints
- [ ] Add rate limiting middleware
- [ ] Fix login HTTP status code (401 instead of 400)
- [ ] Consolidate duplicated code (DRY refactor)
