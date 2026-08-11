import { fetchHealth } from "../../lib/api-client";

export default async function HealthTestPage() {
  try {
    const health = await fetchHealth();

    return (
      <main>
        <h1>Test Backend /health</h1>
        <div className="card">
          <p>
            <strong>status:</strong> {health.status}
          </p>
          <p>
            <strong>service:</strong> {health.service}
          </p>
          {health.version ? (
            <p>
              <strong>version:</strong> {health.version}
            </p>
          ) : null}
        </div>
      </main>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";

    return (
      <main>
        <h1>Test Backend /health</h1>
        <div className="card">
          <p>Impossible de joindre le backend.</p>
          <p className="muted">{message}</p>
          <p className="muted">
            Vérifie NEXT_PUBLIC_API_BASE_URL et le serveur FastAPI.
          </p>
        </div>
      </main>
    );
  }
}
