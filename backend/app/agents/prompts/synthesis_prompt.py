from __future__ import annotations

import mlflow
import mlflow.genai

from backend.app.core.config import get_settings

SYSTEM_PROMPT_NAME = "fiscalmind-synthesis-system"
USER_PROMPT_NAME = "fiscalmind-synthesis-user"
DEFAULT_ALIAS = "production"

# Used both as the seed content for register_initial_prompt_versions() and as the fallback
# returned by load_synthesis_prompt_templates() when the registry is unreachable or the alias
# has not been registered yet (e.g. a fresh checkout before that script has run) — answering a
# question should never hard-depend on the prompt registry being available.
FALLBACK_SYSTEM_PROMPT = (
	"Tu es un assistant juridique specialise en loi de finance tunisienne. "
	"N'invente jamais une source. Cite uniquement les extraits fournis. "
	"Si les informations sont insuffisantes, dis-le explicitement."
)
FALLBACK_USER_PROMPT = (
	"Langue de reponse: {{language}}\n"
	"Categorie estimee: {{category}}\n"
	"Question utilisateur: {{question}}\n"
	"IDs de contexte graphe: {{graph_context_ids}}\n\n"
	"Sources disponibles:\n"
	"{{context_block}}\n\n"
	"Donne une reponse claire, concise, et strictement basee sur ces sources."
)


def load_synthesis_prompt_templates(alias: str = DEFAULT_ALIAS) -> tuple[str, str]:
	"""Returns (system_template, user_template) as raw "{{variable}}" strings, from the MLflow
	Prompt Registry if available, else the hardcoded fallbacks above."""
	settings = get_settings()
	try:
		mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
		system_version = mlflow.genai.load_prompt(f"prompts:/{SYSTEM_PROMPT_NAME}@{alias}")
		user_version = mlflow.genai.load_prompt(f"prompts:/{USER_PROMPT_NAME}@{alias}")
		return system_version.template, user_version.template
	except Exception:
		return FALLBACK_SYSTEM_PROMPT, FALLBACK_USER_PROMPT


def render_prompt(template: str, **variables: str) -> str:
	rendered = template
	for key, value in variables.items():
		rendered = rendered.replace("{{" + key + "}}", str(value))
	return rendered


def register_initial_prompt_versions() -> None:
	"""One-off setup, run via backend/scripts/register_prompts.py — not called on every request
	or app startup. Prompt Registry versions are immutable, so re-running this creates a new
	(identical) version each time rather than updating one in place; it only needs to run once,
	or again when deliberately authoring a new prompt version to alias @production."""
	settings = get_settings()
	mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

	system_version = mlflow.genai.register_prompt(
		name=SYSTEM_PROMPT_NAME,
		template=FALLBACK_SYSTEM_PROMPT,
		commit_message="Initial version, extracted from the hardcoded string previously in synthesis.py",
	)
	mlflow.genai.set_prompt_alias(SYSTEM_PROMPT_NAME, DEFAULT_ALIAS, system_version.version)

	user_version = mlflow.genai.register_prompt(
		name=USER_PROMPT_NAME,
		template=FALLBACK_USER_PROMPT,
		commit_message="Initial version, extracted from the hardcoded string previously in synthesis.py",
	)
	mlflow.genai.set_prompt_alias(USER_PROMPT_NAME, DEFAULT_ALIAS, user_version.version)
