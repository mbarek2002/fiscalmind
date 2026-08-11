from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.db_models import User
from backend.app.models.enums import UserRole
from backend.app.models.schemas import LoginRequest, RefreshRequest, TokenPairResponse, UserCreateRequest, UserPublic
from backend.app.services.auth_service import (
	authenticate_user,
	create_user,
	issue_token_pair,
	rotate_refresh_token,
	to_user_public,
)


router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserPublic)
async def register(payload: UserCreateRequest, db: AsyncSession = Depends(get_db)) -> UserPublic:
	if payload.role != UserRole.citoyen:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Public register can only create citoyen accounts",
		)
	user = await create_user(db, payload)
	return to_user_public(user)


@router.post("/admin/register", response_model=UserPublic)
async def register_admin_managed(
	payload: UserCreateRequest,
	db: AsyncSession = Depends(get_db),
	_: User = Depends(require_roles(UserRole.admin)),
) -> UserPublic:
	user = await create_user(db, payload)
	return to_user_public(user)


@router.post("/login", response_model=TokenPairResponse)
async def login(request: Request, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
	content_type = request.headers.get("content-type", "")
	email: str | None = None
	password: str | None = None

	if "application/x-www-form-urlencoded" in content_type:
		form_data = parse_qs((await request.body()).decode("utf-8"))
		email = (form_data.get("username") or [None])[0]
		password = (form_data.get("password") or [None])[0]
	else:
		try:
			payload = LoginRequest.model_validate_json(await request.body())
		except Exception as exc:
			raise HTTPException(
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
				detail="Request must be JSON or OAuth2 form data",
			) from exc
		email = payload.email
		password = payload.password

	if not email or not password:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="Missing username/password or email/password",
		)

	user = await authenticate_user(db, email, password)
	return await issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
	return await rotate_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
	return to_user_public(current_user)
