from backend.app.agents.prompts.synthesis_prompt import (
	DEFAULT_ALIAS,
	SYSTEM_PROMPT_NAME,
	USER_PROMPT_NAME,
	register_initial_prompt_versions,
)


def main() -> None:
	register_initial_prompt_versions()
	print(f"Registered '{SYSTEM_PROMPT_NAME}' and '{USER_PROMPT_NAME}' @{DEFAULT_ALIAS}")


if __name__ == "__main__":
	main()
