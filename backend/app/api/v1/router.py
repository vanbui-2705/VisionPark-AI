from fastapi import APIRouter

from app.api.v1.endpoints.alpr import router as alpr_router
from app.api.v1.endpoints.lanes import router as lanes_router
from app.modules.auth.router import router as auth_router

from app.modules.audit_logs.router import router as audit_router
from app.modules.parking.router import router as parking_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(lanes_router, tags=["lanes"])
api_router.include_router(alpr_router, prefix="/alpr", tags=["ALPR"])
api_router.include_router(parking_router, tags=["parking"])
api_router.include_router(audit_router, tags=["audit"])
