import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infrastructure.config.settings import settings
from interfaces.api.auth_routes import router as auth_router
from interfaces.api.dataset_routes import router as dataset_router
from interfaces.api.generation_routes import router as generation_router
from interfaces.api.health_routes import router as health_router

# =====================================================
# Logging Setup
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# =====================================================
# App Init
# =====================================================

app = FastAPI(title="Dataset Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# =====================================================
# Global Exception Handler
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# =====================================================
# Register Routers
# =====================================================

app.include_router(auth_router)
app.include_router(dataset_router)
app.include_router(generation_router)
app.include_router(health_router)


# =====================================================
# Run Server
# =====================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)