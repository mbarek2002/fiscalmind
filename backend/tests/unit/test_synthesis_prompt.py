import mlflow.genai

from backend.app.agents.prompts import synthesis_prompt


def test_render_prompt_substitutes_double_brace_variables() -> None:
	rendered = synthesis_prompt.render_prompt(
		"Langue: {{language}}, Question: {{question}}", language="fr", question="Q ?"
	)

	assert rendered == "Langue: fr, Question: Q ?"


def test_render_prompt_leaves_unknown_placeholders_untouched() -> None:
	rendered = synthesis_prompt.render_prompt("{{known}} / {{unknown}}", known="valeur")

	assert rendered == "valeur / {{unknown}}"


def test_load_synthesis_prompt_templates_falls_back_when_registry_unavailable(monkeypatch) -> None:
	def _raise(*args, **kwargs):
		raise RuntimeError("registry unreachable")

	monkeypatch.setattr(mlflow.genai, "load_prompt", _raise)

	system_template, user_template = synthesis_prompt.load_synthesis_prompt_templates()

	assert system_template == synthesis_prompt.FALLBACK_SYSTEM_PROMPT
	assert user_template == synthesis_prompt.FALLBACK_USER_PROMPT
