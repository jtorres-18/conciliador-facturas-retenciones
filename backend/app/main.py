"""Entry point: creates the FastAPI application and registers the routes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.reconciliation_router import router
from app.config import ALLOWED_ORIGINS

app = FastAPI(
    title="Conciliador de facturas y retenciones",
    description="Cruza facturas de proveedores con los registros contables y reporta inconsistencias.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
