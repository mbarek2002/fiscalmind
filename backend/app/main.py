from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings
from backend.app.db.init_db import init_db


settings = get_settings()


app = FastAPI(
	title=settings.app_name,
	version="0.1.0",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
	await init_db()


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
	return {"status": "ok", "service": "backend"}


app.include_router(api_router, prefix="/api/v1")
