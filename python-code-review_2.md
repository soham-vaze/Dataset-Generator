# 🐍 Python Code Review — Dataset Generator (Clean Architecture)

**Reviewer**: Senior Python Engineer (20+ years)  
**Date**: 2026-05-04  
**Scope**: Full exhaustive review of all Python files  
**Standard**: Production-grade, zero-tolerance

---

## 1. 📁 File-wise Review

---

### File: `infrastructure/config/settings.py`

**Line 13**: 🔐 ❌ Hardcoded default database credentials  
The default value contains plaintext credentials (`dataset_user:changeme`). If `.env` is missing in production, the app silently uses insecure defaults.

👉 Suggested Fix:
```python
class Settings(BaseSettings):
    # Database
    database_url: str  # No default — FORCE explicit configuration

    # JWT
    jwt_secret_key: str  # No default — FORCE explicit configuration
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:5173"]

    # Storage
    storage_dir: str = "local_storage"

    # Ollama / LLM API
    ollama_api_url: str = "http://localhost:11434/api/generate"

    # Server
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

**Line 16**: 🔐 ❌ Hardcoded default JWT secret key  
`"change-this-to-a-secure-random-key"` — If `.env` is missing, tokens are signed with a known key. This is a **critical security vulnerability**.

👉 Suggested Fix:
```python
jwt_secret_key: str  # Remove default — fail fast if not configured
```

**Line 27**: 🔐 ⚠️ Hardcoded internal IP in `ollama_api_url`  
`"http://10.30.1.34:11434/api/generate"` — exposes internal network topology. Use a localhost or placeholder default.

👉 Suggested Fix:
```python
ollama_api_url: str = "http://localhost:11434/api/generate"
```

---

### File: `main.py`

**Line 79**: ⚠️ Server binds to `0.0.0.0`  
Binding to all interfaces without documentation. Acceptable for containerized deployments but should be configurable.

👉 Recommendation:
```python
if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
```
Add `host: str = "0.0.0.0"` and `port: int = 8000` to `Settings`.

**Line 1-79**: ✅ Good — proper logging setup, global exception handler, CORS configuration, modular router mounting.

---

### File: `infrastructure/db/database.py`

**Line 9-14**: ⚠️ No `echo` option tied to debug mode  
In development, SQL logging is essential for debugging.

👉 Suggested Fix:
```python
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)
```

**Line 27-32**: 🔁 Code duplication — `get_db()` is defined here AND in `interfaces/api/dependencies.py`  
Two separate session factories with identical logic.

👉 Suggested Fix:  
Remove `get_db()` from `infrastructure/db/database.py` or import it in `dependencies.py` instead of redefining.

---

### File: `infrastructure/db/models.py`

**Line 1-42**: ✅ Good — proper UUID primary keys, proper indexes, timestamps, relationships.

**Line 14**: ⚠️ Missing `Index` on `email` column explicitly (though `unique=True` creates one implicitly)  
This is acceptable but noting for clarity.

---

### File: `infrastructure/db/dataset_repository.py`

**Line 57-62**: ⚠️ Bare `except Exception` without logging  
The rollback is correct, but swallowing context before re-raising loses information.

👉 Suggested Fix:
```python
import logging

logger = logging.getLogger(__name__)

def create(self, entity: DatasetEntity) -> DatasetEntity:
    dataset = Dataset(
        id=entity.id,
        name=entity.name,
        dataset_type=entity.dataset_type,
        format=entity.format,
        storage_key=entity.storage_key,
        status=entity.status,
        user_id=entity.user_id,
    )
    self._db.add(dataset)
    try:
        self._db.commit()
        self._db.refresh(dataset)
    except Exception:
        self._db.rollback()
        logger.error("Failed to create dataset: %s", entity.id, exc_info=True)
        raise
    return self._to_entity(dataset)
```

**Line 70-78**: Same pattern for `delete` — bare except without logging.

**Line 1-78**: ⚠️ No logging import or logger instantiation in this file.

👉 Suggested Fix: Add at top:
```python
import logging
logger = logging.getLogger(__name__)
```

---

### File: `infrastructure/db/user_repository.py`

**Line 40-46**: ⚠️ Same issue — bare `except Exception` without logging.

👉 Suggested Fix: Same as dataset_repository — add logger and log before re-raise.

**Line 1-46**: ⚠️ No logging import.

---

### File: `infrastructure/db/database_init.py`

**Line 1-22**: ✅ Clean, proper logging, exception handling.

---

### File: `domain/entities/user.py`

**Line 1-12**: ✅ Clean dataclass entity. Proper type hints.

---

### File: `domain/entities/dataset.py`

**Line 1-16**: ✅ Clean dataclass entity. Proper type hints.

---

### File: `domain/interfaces/user_repository.py`

**Line 1-20**: ✅ Clean abstract interface. Proper use of ABC.

---

### File: `domain/interfaces/dataset_repository.py`

**Line 1-25**: ✅ Clean abstract interface.

---

### File: `app/services/auth_service.py`

**Line 1-48**: ✅ Good — bcrypt with 72-byte truncation, proper JWT handling, timezone-aware datetime, logging on failure.

**Line 42**: ⚠️ `str | None` union syntax requires Python 3.10+  
If supporting 3.9, use `Optional[str]`.

👉 Suggested Fix:
```python
user_id: Optional[str] = payload.get("sub")
```

---

### File: `app/services/storage_service.py`

**Line 1-48**: ✅ Good — path traversal protection via `is_relative_to`, proper temp file handling.

**Line 26**: ⚠️ `str | None` union syntax — same Python 3.10+ requirement.

---

### File: `app/use_cases/auth.py`

**Line 19**: ⚠️ `ValueError` used for domain error — should use a custom exception.  
Domain-specific exceptions make error handling cleaner at the API layer.

👉 Suggested Fix:
```python
# domain/exceptions.py
class UserAlreadyExistsError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass
```

**Line 37**: ⚠️ `str | None` return type annotation — same 3.10+ issue.

**Line 1-43**: ✅ Otherwise clean separation of concerns.

---

### File: `app/use_cases/generate_dataset.py`

**Line 22-31**: ⚠️ `extract_document_text` opens files without size limits  
A malicious user could upload a multi-GB PDF and exhaust server memory.

👉 Suggested Fix:
```python
import os

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def extract_document_text(file_path: str, filename: str) -> str:
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")
    
    if filename.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file_path)
        pages_text = [page.extract_text() for page in reader.pages]
        return "\n".join(pages_text)
    else:
        raise ValueError("Unsupported file format. Only .txt and .pdf are supported.")
```

**Line 29**: ⚡ String concatenation in loop for PDF text extraction — inefficient.

👉 Suggested Fix:
```python
pages_text = [page.extract_text() for page in reader.pages]
return "\n".join(pages_text)
```

**Line 54-76**: 🔁 All `generate_*` functions follow identical pattern: create context → call generator → save metadata → return ID. Consider a template method or decorator.

---

### File: `app/use_cases/manage_dataset.py`

**Line 34-37**: ❌ 🐛 File deletion happens before DB deletion — if DB delete fails, file is already gone (data inconsistency).

👉 Suggested Fix:
```python
def delete_dataset(
    dataset_id: UUID,
    user_id: UUID,
    dataset_repo: DatasetRepositoryInterface,
    storage: StorageService,
) -> bool:
    entity = dataset_repo.find_by_id_and_user(dataset_id, user_id)
    if not entity:
        return False

    # Delete from DB first, then file
    deleted = dataset_repo.delete(dataset_id, user_id)
    if not deleted:
        return False

    file_path = storage.get_storage_path(entity.storage_key)
    if file_path.exists():
        file_path.unlink()

    return True
```

---

### File: `interfaces/api/dependencies.py`

**Line 40-45**: 🔁 Duplicate `get_db()` — already defined in `infrastructure/db/database.py`.

👉 Suggested Fix:
```python
from infrastructure.db.database import get_db
```

**Line 56-74**: ✅ Good — proper JWT validation, user lookup, proper HTTP 401 response.

---

### File: `interfaces/api/auth_routes.py`

**Line 20**: ❌ Return type annotation `-> dict` is too vague for a typed codebase.

👉 Suggested Fix:
```python
@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserEntity = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=str(current_user.id), email=current_user.email)
```

**Line 30-33**: ⚠️ Exception message from Pydantic validation exposed directly to client via `str(e)`.  
Pydantic errors can contain internal field names and schema details.

👉 Suggested Fix:
```python
from pydantic import ValidationError

try:
    validated = RegisterRequest(email=email, password=password)
except ValidationError:
    raise HTTPException(status_code=400, detail="Invalid email or password format")
```

**Line 20-62**: ⚠️ All route functions return `-> dict` — should return typed response models.

---

### File: `interfaces/api/dataset_routes.py`

**Line 28-40**: ⚠️ No pagination on `list_datasets` endpoint.  
If a user has thousands of datasets, this returns them all at once.

👉 Suggested Fix:
```python
@router.get("/datasets")
def list_datasets_route(
    dataset_type: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    datasets = list_datasets(dataset_type, current_user.id, dataset_repo, skip=skip, limit=limit)
    ...
```

**Line 50-57**: ⚠️ `FileResponse` without content-disposition header validation — filename comes from entity name (user-controlled). Already prefixed with `.csv` which is fine, but entity name should be sanitized.

---

### File: `interfaces/api/generation_routes.py`

**Line 30-60**: ⚡ ❌ Synchronous blocking I/O in route handlers  
All generation routes call `generate_*` functions that make HTTP requests to Ollama API (via `requests.post`) — these are **blocking calls** in synchronous FastAPI route handlers. Under load, this will exhaust the thread pool and block the entire server.

👉 Suggested Fix:  
Either:
1. Convert to `async def` routes with `httpx.AsyncClient` in generators, OR
2. Use background tasks / task queue:
```python
from fastapi import BackgroundTasks

@router.post("/sft", response_model=DatasetResponse)
async def sft_dataset(
    ...
    background_tasks: BackgroundTasks,
) -> dict:
    # Queue generation as background task
    # Return immediately with job ID
    ...
```

**Line 87-107**: ⚠️ No file type validation for `schema_file` upload.  
Only filename extension checked via `sanitize_filename` but no MIME type or content validation.

**Line 160-171**: ⚠️ `class_labels: str = Form("class1,class2")` — default value in production Form is confusing. Should be required.

👉 Suggested Fix:
```python
class_labels: str = Form(..., description="Comma-separated class labels")
```

**Line 30-250**: 🔁 Heavy code duplication across all 6 route handlers — identical try/except/logging pattern.

---

### File: `interfaces/schemas/auth.py`

**Line 1-23**: ✅ Good — email validation via `EmailStr`, password length check.

**Line 9-12**: ⚠️ Password validation is minimal — only length check. No complexity requirements.

👉 Recommendation: Add basic complexity validation:
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

**Line 1-9**: ✅ Clean schemas.

---

### File: `interfaces/api/health_routes.py`

**Line 1-9**: ✅ Minimal health check — acceptable.

**Line 7-8**: ⚠️ Health check doesn't verify database connectivity.

👉 Recommendation:
```python
from sqlalchemy import text
from infrastructure.db.database import SessionLocal
from fastapi.responses import JSONResponse

@router.get("/health")
def health_check() -> dict:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "db": "disconnected"})
```

---

### File: `generators/utils.py`

**Line 17**: ⚠️ Mutable global state (`_api_url`) — not thread-safe.  
Module-level global modified by `configure()` is a race condition risk in multi-worker deployments.

👉 Suggested Fix:
```python
import threading

_lock = threading.Lock()
_api_url: str = "http://localhost:11434/api/generate"

def configure(api_url: str) -> None:
    global _api_url
    with _lock:
        _api_url = api_url
```

**Line 50-63**: ⚡ `requests.post` is synchronous — blocks the event loop if called from async context. See generation_routes issue above.

**Line 87-96**: ⚠️ `extract_json` — `re.findall(r"\{[\s\S]*\}", text)` is greedy and can match too broadly on large outputs.

---

### File: `generators/sft.py`

**Line 159-168**: ⚠️ Hardcoded file path in `__main__` block — not an issue for production but should be parameterized.

**Line 60-67**: ⚡ Loading entire CSV into memory for deduplication on every call.  
For large existing datasets, this is a memory concern.

**Line 1-168**: ✅ Good — proper logging, deduplication, quality filtering, batch processing.

---

### File: `generators/nl_sql.py`

**Line 103-108**: 🔐 ❌ SQL Injection risk in DDL generation  
`json_to_sqlite_ddl` constructs DDL statements via string concatenation from user-provided schema JSON (table names, column names). If schema file contains malicious identifiers, they are injected directly into SQL.

👉 Suggested Fix:
```python
import re

def sanitize_identifier(name: str) -> str:
    """Allow only safe SQL identifiers."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name

def json_to_sqlite_ddl(schema):
    ddl_statements = []
    column_map = {}

    for table in schema["tables"]:
        table_name = sanitize_identifier(table["table_name"])
        column_defs = []
        column_map[table_name] = []

        for col in table["columns"]:
            col_name = sanitize_identifier(col["name"])
            col_type = sanitize_identifier(col["type"])
            col_def = f"{col_name} {col_type}"
            if col.get("primary_key"):
                col_def += " PRIMARY KEY"
            column_defs.append(col_def)
            column_map[table_name].append(col_name)

        ddl = f"CREATE TABLE {table_name} ({', '.join(column_defs)});"
        ddl_statements.append(ddl)

    return ddl_statements, column_map
```

**Line 213-215**: ⚠️ `sqlite3.connect(":memory:")` inside a loop for validation — acceptable for small queries but creates overhead for bulk generation.

---

### File: `generators/rag.py`

**Line 1-8**: ⚠️ `import ollama` — direct SDK import couples this generator to Ollama. Other generators use HTTP via `call_model`. Inconsistent approach.

**Line 14-20**: ⚠️ NLTK download at import time — side effect during module load. Can fail silently or slow startup.

👉 Suggested Fix: Move downloads to an explicit `setup()` function called at app startup.

**Line 224-236**: ⚡ `ollama.embeddings()` is a synchronous HTTP call made per-pair inside a loop. For large documents this is very slow.

👉 Recommendation: Batch embeddings or use async.

---

### File: `generators/code.py`

**Line 1-172**: 🔁 Heavy structural duplication with `generators/sft.py` — same loop/retry/dedup/quality-filter/save pattern.

👉 Suggested Fix: Extract a generic batch generation utility:
```python
def generate_with_retry(
    prompt_builder: Callable[[int], str],
    result_parser: Callable[[Dict], List[Dict]],
    quality_filter: Callable[[Dict], bool],
    dedup_key: Callable[[Dict], str],
    num_samples: int,
    model: str,
    output_path: str,
    ...
) -> List[Dict]:
    ...
```

---

### File: `generators/classification.py`

**Line 1-100**: 🔁 Same batch generation pattern duplicated again.

---

### File: `generators/multilingual.py`

**Line 1-250**: ✅ Good — proper Argos Translate integration, language validation.

**Line 65-74**: ⚠️ `LANGUAGE_MAP` hardcoded — acceptable but could be loaded from config for extensibility.

---

### File: `generators/dataset.py`

**Line 74-87**: ⚠️ `system_content` variable defined inside function but contains hardcoded prompt text.

**Line 84-91**: ⚡ Deep retry loop (5 retries × n batches) with 300s timeout per call — a single story could block for 25+ minutes.

**Line 86**: ⚠️ Unused `system_content` variable — it's defined but never sent to `call_model()` (which doesn't support system messages). Dead code.

---

### File: `generators/automate_gen.py`

**Line 43-49**: 🔐 ⚠️ `subprocess.run` with user-influenced arguments  
The `story`, `epic`, `feature` values from the JSON file are passed directly to `subprocess.run`. While `check=True` and list-form (no shell=True) mitigate shell injection, the command calls `python3` with user-provided strings as CLI args — this is a risk vector if the JSON file is untrusted.

👉 Suggested Fix:
```python
def sanitize_arg(value: str) -> str:
    """Validate CLI argument length and content."""
    if not value or len(value) > 500:
        raise ValueError(f"Invalid argument length: {len(value) if value else 0}")
    return value

command: List[str] = [
    sys.executable, generator_script,
    "--epic", sanitize_arg(epic),
    "--feature", sanitize_arg(feature),
    "--story", sanitize_arg(story),
    "--model", model,
    "--batches", "1"
]
```

**Line 31**: ⚠️ Hardcoded `"python3"` — not portable (Windows uses `python`).

👉 Suggested Fix:
```python
import sys
command = [sys.executable, generator_script, ...]
```

---

## 2. 🚨 Critical Issues (Must Fix Before Merge)

| # | Category | File | Issue |
|---|----------|------|-------|
| 1 | 🔐 Security | `infrastructure/config/settings.py:13,16` | Hardcoded DB credentials and JWT secret as defaults — if `.env` is missing, app runs with known secrets |
| 2 | 🔐 Security | `generators/nl_sql.py:103-108` | SQL identifiers from user-provided JSON concatenated directly into DDL — potential SQL injection |
| 3 | ⚡ Performance | `interfaces/api/generation_routes.py:*` | All generation endpoints are synchronous and make blocking HTTP calls — will exhaust thread pool under concurrent load |
| 4 | 🐛 Bug | `app/use_cases/manage_dataset.py:34-37` | File deleted before DB record — if DB delete fails, data is lost (inconsistency) |
| 5 | 🔐 Security | `infrastructure/config/settings.py:27` | Internal IP address (`10.30.1.34`) hardcoded in default config — exposes internal topology |
| 6 | ⚡ Performance | `generators/rag.py:224-236` | Synchronous embedding calls per-pair inside loop — extremely slow for large documents |

---

## 3. ⚠️ Improvements (Should Fix)

| # | Category | File | Issue |
|---|----------|------|-------|
| 1 | 🔁 DRY | `generators/sft.py`, `code.py`, `classification.py` | Identical batch-generate-retry-dedup-save pattern repeated 3+ times |
| 2 | 🔁 DRY | `interfaces/api/dependencies.py:40-45` | `get_db()` duplicated from `infrastructure/db/database.py` |
| 3 | 🔁 DRY | `interfaces/api/generation_routes.py` | 6 route handlers with identical try/except/logging pattern |
| 4 | Architecture | `generators/rag.py` | Direct `ollama` SDK import while all other generators use shared `call_model()` |
| 5 | Consistency | `app/services/auth_service.py:42`, `storage_service.py:26` | `str \| None` syntax requires Python 3.10+ — inconsistent with broader compatibility |
| 6 | Robustness | `interfaces/api/dataset_routes.py` | No pagination on `GET /datasets` endpoint |
| 7 | Robustness | `app/use_cases/generate_dataset.py:22-31` | No file size limit on uploaded documents |
| 8 | Logging | `infrastructure/db/dataset_repository.py`, `user_repository.py` | No logger — errors swallowed silently before re-raise |
| 9 | Type Safety | `interfaces/api/auth_routes.py` | All routes return `-> dict` instead of typed response models |
| 10 | Exception Handling | `app/use_cases/auth.py:19` | Generic `ValueError` for domain errors instead of custom exceptions |

---

## 4. 💡 Best Practice Suggestions

1. **Background Task Queue**: Replace synchronous generation with Celery/ARQ task queue. Generation can take minutes — HTTP request should return immediately with a job ID.

2. **Rate Limiting**: No rate limiting on generation endpoints. A single user could overwhelm the LLM backend.

3. **Input Validation on Generators**: `num_samples`, `temperature`, `batch_size` parameters have no upper-bound validation. A request with `num_samples=1000000` will run indefinitely.

4. **Unified Error Handling**: Create a custom exception hierarchy:
   ```python
   class AppError(Exception): ...
   class NotFoundError(AppError): ...
   class ValidationError(AppError): ...
   class GenerationError(AppError): ...
   ```
   Handle centrally in middleware.

5. **Async HTTP Client**: Replace `requests` with `httpx.AsyncClient` for LLM API calls.

6. **Alembic Migrations**: `database_init.py` uses `create_all()` — not suitable for production schema evolution. Alembic is in requirements but not wired.

7. **Testing**: **Zero test files found** in the entire codebase. No unit tests, no integration tests, no fixtures.

8. **Docker/Container Config**: No Dockerfile or docker-compose found. Deployment story is unclear.

9. **API Versioning**: No `/v1/` prefix on routes. Breaking changes will affect all clients.

10. **Request ID Tracing**: Add request-id middleware for distributed tracing / log correlation.

---

## 5. 📊 Summary

| Category | Score |
|----------|-------|
| Naming Conventions | **90**/100 |
| Architecture | **82**/100 |
| Type Safety | **70**/100 |
| Logging | **75**/100 |
| Exception Handling | **60**/100 |
| Async/Await | **30**/100 |
| API Design | **70**/100 |
| Validation | **55**/100 |
| Security | **45**/100 |
| DRY | **50**/100 |
| Performance | **40**/100 |
| Configuration | **55**/100 |
| Testing | **0**/100 |
| **Overall Python Code Quality** | **52**/100 |

---

## Final Verdict

### ❌ Not Ready for Production

**Justification:**

1. **Zero test coverage** — no tests exist anywhere in the codebase.
2. **Critical security vulnerabilities** — hardcoded JWT secret, hardcoded DB credentials as defaults, SQL identifier injection in NL-SQL generator.
3. **Blocking I/O in all generation routes** — synchronous `requests.post` calls to LLM API will deadlock the server under any concurrent load.
4. **No rate limiting or input bounds** — generation endpoints can be abused to exhaust compute resources.
5. **Data integrity bug** — file deletion before DB commit in dataset deletion flow.
6. **Significant DRY violations** — the same 50-line pattern is copy-pasted across 4+ generator files.

**Minimum requirements to pass:**
- [ ] Remove all hardcoded secrets/credentials from defaults
- [ ] Add input validation bounds (max file size, max samples, temperature range)
- [ ] Fix delete ordering (DB first, then file)
- [ ] Sanitize SQL identifiers in NL-SQL generator
- [ ] Add at minimum integration tests for auth flow and CRUD operations
- [ ] Either convert to async or use background task queue for generation
- [ ] Add rate limiting on generation endpoints
