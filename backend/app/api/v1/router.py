from fastapi import APIRouter

from backend.app.api.v1.endpoints.auth import router as auth_router
from backend.app.api.v1.endpoints.companies import router as companies_router
from backend.app.api.v1.endpoints.debug_ingestion import router as debug_ingestion_router
from backend.app.api.v1.endpoints.documents import router as documents_router
from backend.app.api.v1.endpoints.financial_submissions import router as financial_submissions_router
from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.endpoints.query import router as query_router
from backend.app.api.v1.endpoints.users import router as users_router


api_router = APIRouter()
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(query_router, tags=["query"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(users_router, tags=["users"])
api_router.include_router(companies_router, tags=["companies"])
api_router.include_router(financial_submissions_router, tags=["financial-submissions"])
api_router.include_router(debug_ingestion_router, tags=["debug"])
