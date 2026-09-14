"""API路由导出"""
from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.payment_accounts import router as payment_accounts_router
from app.api.orders import router as orders_router
from app.api.shareholders import router as shareholders_router
from app.api.share_rules import router as share_rules_router
from app.api.share_records import router as share_records_router
from app.api.settlements import router as settlements_router
from app.api.reconciliations import router as reconciliations_router
from app.api.dashboard import router as dashboard_router
from app.api.uploads import router as uploads_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(payment_accounts_router)
api_router.include_router(orders_router)
api_router.include_router(shareholders_router)
api_router.include_router(share_rules_router)
api_router.include_router(share_records_router)
api_router.include_router(settlements_router)
api_router.include_router(reconciliations_router)
api_router.include_router(dashboard_router)
api_router.include_router(uploads_router)
