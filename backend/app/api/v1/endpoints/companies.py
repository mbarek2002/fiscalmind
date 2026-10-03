from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db, require_roles
from backend.app.models.db_models import Company, User
from backend.app.models.enums import UserRole
from backend.app.models.schemas import CompanyCreateRequest, CompanyPublic


router = APIRouter(prefix="/companies")


def _to_company_public(company: Company) -> CompanyPublic:
	return CompanyPublic(
		id=company.id,
		name=company.name,
		matricule_fiscal=company.matricule_fiscal,
		secteur_activite=company.secteur_activite,
		created_at=company.created_at,
	)


@router.post("", response_model=CompanyPublic, status_code=status.HTTP_201_CREATED)
async def create_company(
	payload: CompanyCreateRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise, UserRole.admin)),
) -> CompanyPublic:
	existing = await db.execute(select(Company).where(Company.matricule_fiscal == payload.matricule_fiscal))
	if existing.scalar_one_or_none() is not None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Matricule fiscal already registered")

	company = Company(
		name=payload.name,
		matricule_fiscal=payload.matricule_fiscal,
		secteur_activite=payload.secteur_activite,
		created_by=current_user.id,
	)
	db.add(company)
	await db.flush()
	if current_user.company_id is None:
		current_user.company_id = company.id
	await db.commit()
	await db.refresh(company)
	return _to_company_public(company)


@router.get("/me", response_model=CompanyPublic)
async def get_my_company(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise)),
) -> CompanyPublic:
	if current_user.company_id is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No company linked to this account")
	result = await db.execute(select(Company).where(Company.id == current_user.company_id))
	company = result.scalar_one_or_none()
	if company is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
	return _to_company_public(company)


@router.get("/{company_id}", response_model=CompanyPublic)
async def get_company(
	company_id: str,
	db: AsyncSession = Depends(get_db),
	_: User = Depends(require_roles(UserRole.admin)),
) -> CompanyPublic:
	result = await db.execute(select(Company).where(Company.id == company_id))
	company = result.scalar_one_or_none()
	if company is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
	return _to_company_public(company)
