"""CUSTOS web application entry point.

Business logic lives in capabilities/ and engine/. HTTP concerns live in
routers/, while templates and static assets own the presentation layer.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.core.config import STATIC_DIR
from backend.routers.api import router as api_router
from backend.routers.pages import router as pages_router

app = FastAPI(title="CUSTOS", version="2.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(api_router, prefix="/api", tags=["operations"])
app.include_router(pages_router)
