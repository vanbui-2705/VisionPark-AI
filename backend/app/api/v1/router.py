from fastapi import APIRouter

from app.api.v1.endpoints.alpr import router as alpr_router
from app.api.v1.endpoints.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.lanes import router as lanes_router
from app.api.v1.endpoints.parking import router as parking_router
from app.modules.auth.router import router as auth_router
from app.modules.buildings.router import router as buildings_router
from app.modules.checkout.router import router as checkout_router
from app.modules.lot_settings.router import router as lot_settings_router
from app.modules.operations.router import router as operations_router
from app.modules.pricing.billing_router import router as billing_router
from app.modules.pricing.router import router as pricing_router
from app.modules.pricing.tickets_router import router as tickets_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(lanes_router, tags=["lanes"])
api_router.include_router(alpr_router, prefix="/alpr", tags=["ALPR"])
api_router.include_router(parking_router)
api_router.include_router(checkout_router)
api_router.include_router(buildings_router)
api_router.include_router(pricing_router)
api_router.include_router(billing_router)
api_router.include_router(tickets_router)
api_router.include_router(audit_logs_router)
api_router.include_router(users_router)
api_router.include_router(lot_settings_router)
api_router.include_router(operations_router)
