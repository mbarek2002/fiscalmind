from collections.abc import AsyncGenerator, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import decode_token
from backend.app.db.session import get_db_session
from backend.app.models.db_models import User
from backend.app.models.enums import UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
	async for session in get_db_session():
		yield session


async def get_current_user(
	token: str = Depends(oauth2_scheme),
	db: AsyncSession = Depends(get_db),
) -> User:
	try:
		payload = decode_token(token)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid authentication credentials",
		) from exc

	if payload.get("typ") != "access":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

	user_id = payload.get("sub")
	if not user_id:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject missing")

	result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
	user = result.scalar_one_or_none()
	if user is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
	return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
	async def _checker(current_user: User = Depends(get_current_user)) -> User:
		if current_user.role not in allowed_roles:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
		return current_user

	return _checker
