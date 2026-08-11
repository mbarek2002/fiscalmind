from fastapi.testclient import TestClient
from uuid import uuid4


def test_health_endpoint(client: TestClient) -> None:
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json()["status"] == "ok"


def test_query_endpoint_returns_expected_shape(client: TestClient) -> None:
	email = f"user-{uuid4()}@example.tn"
	register_payload = {
		"email": email,
		"password": "Password123!",
		"full_name": "User Test",
		"role": "citoyen",
		"preferred_lang": "fr",
	}
	register_response = client.post("/api/v1/auth/register", json=register_payload)
	assert register_response.status_code == 200

	login_response = client.post(
		"/api/v1/auth/login",
		json={"email": email, "password": "Password123!"},
	)
	assert login_response.status_code == 200
	tokens = login_response.json()
	access_token = tokens["access_token"]

	payload = {
		"question": "Quelle sanction pour une non declaration de TVA ?",
		"language": "fr",
	}

	response = client.post(
		"/api/v1/query",
		json=payload,
		headers={"Authorization": f"Bearer {access_token}"},
	)
	data = response.json()

	assert response.status_code == 200
	assert "query_id" in data
	assert data["verification_status"] in {"validated", "rejected"}
	assert "final_answer" in data
	assert "disclaimer" in data
	assert "citations" in data
	assert isinstance(data["citations"], list)
	if data["citations"]:
		first = data["citations"][0]
		assert "article_id" in first
		assert "extrait" in first
		assert "loi" in first


def test_query_requires_authentication(client: TestClient) -> None:
	response = client.post(
		"/api/v1/query",
		json={"question": "test sans token", "language": "fr"},
	)

	assert response.status_code == 401
