"""Agrupador de la API versión 1."""

from fastapi import APIRouter

from app.api.v1.endpoints import busquedas, leads

api_router = APIRouter(prefix="/v1")
api_router.include_router(busquedas.router)
api_router.include_router(leads.router)
