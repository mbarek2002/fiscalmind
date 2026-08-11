from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.security import (
	create_access_token,
	create_refresh_token,
	decode_token,
	get_password_hash,
	hash_token,
	verify_password,
)
from backend.app.models.db_models import RefreshToken, User
from backend.app.models.enums import UserRole
from backend.app.models.schemas import TokenPairResponse, UserCreateRequest, UserPublic


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
	result = await db.execute(select(User).where(User.email == email))
	return result.scalar_one_or_none()


async def create_user(db: AsyncSession, payload: UserCreateRequest) -> User:
	existing = await get_user_by_email(db, payload.email)
	if existing is not None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

	user = User(
		email=payload.email,
		hashed_password=get_password_hash(payload.password),
		full_name=payload.full_name,
		role=payload.role,
		preferred_lang=payload.preferred_lang,
	)
	db.add(user)
	await db.commit()
	await db.refresh(user)
	return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
	user = await get_user_by_email(db, email)
	if user is None or not verify_password(password, user.hashed_password):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
	if not user.is_active:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
	return user


def to_user_public(user: User) -> UserPublic:
	return UserPublic(
		id=user.id,
		email=user.email,
		full_name=user.full_name,
		role=user.role,
		is_active=user.is_active,
		preferred_lang=user.preferred_lang,
		created_at=user.created_at,
	)


async def _store_refresh_token(db: AsyncSession, user_id: str, refresh_token: str) -> None:
	settings = get_settings()
	expires_at = datetime.now(UTC) + timedelta(minutes=settings.refresh_token_expire_minutes)
	row = RefreshToken(
		user_id=user_id,
		token_hash=hash_token(refresh_token),
		expires_at=expires_at,
	)
	db.add(row)
	await db.commit()


async def issue_token_pair(db: AsyncSession, user: User) -> TokenPairResponse:
	access_token = create_access_token(subject=user.id, role=user.role.value)
	refresh_token = create_refresh_token(subject=user.id, role=user.role.value)
	await _store_refresh_token(db, user.id, refresh_token)

	return TokenPairResponse(
		access_token=access_token,
		refresh_token=refresh_token,
		user=to_user_public(user),
	)


async def rotate_refresh_token(db: AsyncSession, refresh_token: str) -> TokenPairResponse:
	try:
		payload = decode_token(refresh_token)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

	if payload.get("typ") != "refresh":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not a refresh token")

	token_hash = hash_token(refresh_token)
	token_result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
	token_row = token_result.scalar_one_or_none()
	if token_row is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not recognized")
	if token_row.revoked_at is not None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token already revoked")
	if token_row.expires_at < datetime.now(UTC):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

	user_result = await db.execute(select(User).where(User.id == token_row.user_id, User.is_active.is_(True)))
	user = user_result.scalar_one_or_none()
	if user is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

	token_row.revoked_at = datetime.now(UTC)
	await db.commit()

	return await issue_token_pair(db, user)


def require_admin_role(role: UserRole) -> None:
	if role != UserRole.admin:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create privileged accounts")
