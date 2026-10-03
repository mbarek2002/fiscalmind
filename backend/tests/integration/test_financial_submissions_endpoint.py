from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.db_models import Company, User
from backend.app.models.enums import UserRole


async def _create_user(*, role: UserRole, company_id: str | None = None) -> User:
	async with AsyncSessionLocal() as session:
		user = User(
			email=f"{role.value}-{uuid4()}@example.tn",
			hashed_password=get_password_hash("Password123!"),
			full_name=f"Test {role.value}",
			role=role,
			is_active=True,
			company_id=company_id,
		)
		session.add(user)
		await session.commit()
		await session.refresh(user)
		return user


async def _create_company(*, created_by: str) -> Company:
	async with AsyncSessionLocal() as session:
		company = Company(
			name=f"Societe Test {uuid4()}",
			matricule_fiscal=f"MF-{uuid4().hex[:10]}",
			created_by=created_by,
		)
		session.add(company)
		await session.commit()
		await session.refresh(company)
		return company


def _entreprise_user_with_company() -> User:
	admin = asyncio.run(_create_user(role=UserRole.admin))
	company = asyncio.run(_create_company(created_by=admin.id))
	return asyncio.run(_create_user(role=UserRole.entreprise, company_id=company.id))


def _auth_headers(user: User) -> dict[str, str]:
	token = create_access_token(subject=user.id, role=user.role.value)
	return {"Authorization": f"Bearer {token}"}


def test_create_submission_requires_authentication(client: TestClient) -> None:
	response = client.post("/api/v1/financial-submissions", json={"source_type": "formulaire"})

	assert response.status_code == 401


def test_create_submission_rejects_non_entreprise_role(client: TestClient) -> None:
	citoyen = asyncio.run(_create_user(role=UserRole.citoyen))

	response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "formulaire"},
		headers=_auth_headers(citoyen),
	)

	assert response.status_code == 403


def test_create_submission_without_company_returns_422(client: TestClient) -> None:
	entreprise_sans_societe = asyncio.run(_create_user(role=UserRole.entreprise, company_id=None))

	response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "texte_libre", "free_text": "Chiffre d'affaires en baisse ce trimestre."},
		headers=_auth_headers(entreprise_sans_societe),
	)

	assert response.status_code == 422


def test_create_submission_success_has_no_documents_or_findings(client: TestClient) -> None:
	user = _entreprise_user_with_company()

	response = client.post(
		"/api/v1/financial-submissions",
		json={
			"source_type": "formulaire",
			"structured_data": {"chiffre_affaires": 850000, "tva_collectee": 130000, "tva_deduite": 95000},
		},
		headers=_auth_headers(user),
	)

	assert response.status_code == 201
	data = response.json()
	assert data["company_id"] == user.company_id
	assert data["source_type"] == "formulaire"
	assert data["status"] == "pending"
	assert data["structured_data"] == {"chiffre_affaires": 850000, "tva_collectee": 130000, "tva_deduite": 95000}
	assert data["documents"] == []
	assert data["findings"] == []


def test_list_submissions_scoped_to_own_company(client: TestClient) -> None:
	user_a = _entreprise_user_with_company()
	user_b = _entreprise_user_with_company()

	client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "texte_libre", "free_text": "Situation entreprise A"},
		headers=_auth_headers(user_a),
	)

	response_a = client.get("/api/v1/financial-submissions", headers=_auth_headers(user_a))
	response_b = client.get("/api/v1/financial-submissions", headers=_auth_headers(user_b))

	assert response_a.status_code == 200
	assert response_b.status_code == 200
	assert len(response_a.json()) >= 1
	assert all(item["company_id"] == user_a.company_id for item in response_a.json())
	assert all(item["company_id"] != user_a.company_id for item in response_b.json())


def test_get_submission_not_owned_returns_403(client: TestClient) -> None:
	owner = _entreprise_user_with_company()
	stranger = _entreprise_user_with_company()

	create_response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "texte_libre", "free_text": "Donnees confidentielles"},
		headers=_auth_headers(owner),
	)
	submission_id = create_response.json()["id"]

	response = client.get(f"/api/v1/financial-submissions/{submission_id}", headers=_auth_headers(stranger))

	assert response.status_code == 403


def test_upload_document_switches_source_type_to_mixte(client: TestClient) -> None:
	user = _entreprise_user_with_company()
	create_response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "formulaire", "structured_data": {"chiffre_affaires": 100000}},
		headers=_auth_headers(user),
	)
	submission_id = create_response.json()["id"]

	upload_response = client.post(
		f"/api/v1/financial-submissions/{submission_id}/documents",
		headers=_auth_headers(user),
		files={"file": ("releve.txt", b"Extrait de compte annuel.", "text/plain")},
	)
	assert upload_response.status_code == 201
	assert upload_response.json()["filename"] == "releve.txt"
	assert upload_response.json()["status"] == "uploaded"

	detail_response = client.get(f"/api/v1/financial-submissions/{submission_id}", headers=_auth_headers(user))
	assert detail_response.json()["source_type"] == "mixte"
	assert len(detail_response.json()["documents"]) == 1


def test_upload_document_rejects_unsupported_extension(client: TestClient) -> None:
	user = _entreprise_user_with_company()
	create_response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "formulaire", "structured_data": {}},
		headers=_auth_headers(user),
	)
	submission_id = create_response.json()["id"]

	response = client.post(
		f"/api/v1/financial-submissions/{submission_id}/documents",
		headers=_auth_headers(user),
		files={"file": ("image.png", b"\x89PNG", "image/png")},
	)

	assert response.status_code == 422


def test_analyze_submission_runs_pipeline_and_produces_a_finding(client: TestClient) -> None:
	user = _entreprise_user_with_company()
	create_response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "texte_libre", "free_text": "Retard de paiement de TVA constate."},
		headers=_auth_headers(user),
	)
	submission_id = create_response.json()["id"]
	assert create_response.json()["status"] == "pending"

	response = client.post(f"/api/v1/financial-submissions/{submission_id}/analyze", headers=_auth_headers(user))

	assert response.status_code == 200
	data = response.json()
	# Single-agent pipeline (qualify -> retrieve -> synthesize -> verify) runs for real now via
	# the LangGraph node; one InfractionFinding is produced per submission (not yet split by
	# category — that's a planned future step).
	assert data["status"] == "completed"
	assert data["verification_status"] in {"validated", "rejected"}
	assert len(data["findings"]) == 1
	finding = data["findings"][0]
	assert finding["categorie_infraction"]
	assert finding["description"]


def test_analyze_submission_is_idempotent_when_already_completed(client: TestClient) -> None:
	user = _entreprise_user_with_company()
	create_response = client.post(
		"/api/v1/financial-submissions",
		json={"source_type": "texte_libre", "free_text": "Retard de paiement de TVA constate."},
		headers=_auth_headers(user),
	)
	submission_id = create_response.json()["id"]

	first = client.post(f"/api/v1/financial-submissions/{submission_id}/analyze", headers=_auth_headers(user))
	second = client.post(f"/api/v1/financial-submissions/{submission_id}/analyze", headers=_auth_headers(user))

	assert first.status_code == 200
	assert second.status_code == 200
	assert second.json()["status"] == "completed"
	# Re-analyzing an already-completed submission short-circuits rather than creating a
	# second finding.
	assert len(second.json()["findings"]) == len(first.json()["findings"])
