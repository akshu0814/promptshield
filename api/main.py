import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.database import create_tables
from scanner.rule_engine import get_engine
from scanner.ml_classifier import get_classifier
from middleware.rate_limiter import rate_limit_middleware
from routes.scan import router as scan_router
from routes.events import router as events_router
from routes.stats import router as stats_router
from routes.rules import router as rules_router
from routes.analytics import router as analytics_router
from routes.apps import router as apps_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PromptShield API…")
    create_tables()
    engine = get_engine()
    logger.info("Rule engine ready — %d rules loaded", engine.rule_count)
    classifier = get_classifier()
    if classifier.is_loaded:
        logger.info("ML classifier ready")
    else:
        logger.info("ML classifier not loaded — running regex-only mode")
    yield
    logger.info("PromptShield API shutting down")


app = FastAPI(
    title="PromptShield",
    description="Open-source LLM prompt injection defense API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    # Skip auth for docs, openapi schema, and health check
    if request.url.path in ("/", "/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    if API_SECRET_KEY:
        provided = request.headers.get("X-API-Key", "")
        if provided != API_SECRET_KEY:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing X-API-Key header"},
            )
    return await call_next(request)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "PromptShield", "version": "1.0.0", "status": "ok"}


@app.get("/health", include_in_schema=False)
def health():
    engine = get_engine()
    return {"status": "ok", "rules_loaded": engine.rule_count}


app.include_router(scan_router, tags=["Scanning"])
app.include_router(events_router, tags=["Events"])
app.include_router(stats_router, tags=["Stats"])
app.include_router(rules_router, tags=["Rules"])
app.include_router(analytics_router, tags=["Analytics"])
app.include_router(apps_router, tags=["Apps"])
