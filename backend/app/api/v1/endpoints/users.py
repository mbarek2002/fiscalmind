from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.db_models import User
from backend.app.models.schemas import UpdateProfileRequest, UserPublic
from backend.app.services.auth_service import to_user_public


router = APIRouter(prefix="/users")


@router.patch("/me", response_model=UserPublic)
async def update_profile(
	payload: UpdateProfileRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> UserPublic:
	if payload.full_name is not None:
		current_user.full_name = payload.full_name
	if payload.preferred_lang is not None:
		current_user.preferred_lang = payload.preferred_lang

	await db.commit()
	await db.refresh(current_user)
	return to_user_public(current_user)
