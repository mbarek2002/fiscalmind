from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
	return pwd_context.hash(password)


def _create_token(subject: str, role: str, token_type: str, expires_delta: timedelta) -> str:
	settings = get_settings()
	expire = datetime.now(UTC) + expires_delta
	payload: dict[str, Any] = {
		"sub": subject,
		"role": role,
		"typ": token_type,
		"exp": expire,
		"iat": datetime.now(UTC),
	}
	return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str) -> str:
	settings = get_settings()
	return _create_token(
		subject=subject,
		role=role,
		token_type="access",
		expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
	)


def create_refresh_token(subject: str, role: str) -> str:
	settings = get_settings()
	return _create_token(
		subject=subject,
		role=role,
		token_type="refresh",
		expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
	)


def decode_token(token: str) -> dict[str, Any]:
	settings = get_settings()
	try:
		return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
	except JWTError as exc:
		raise ValueError("Invalid token") from exc


def hash_token(token: str) -> str:
	return sha256(token.encode("utf-8")).hexdigest()
