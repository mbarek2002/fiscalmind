from enum import Enum


class Provider(str, Enum):
	local = "local"
	openai = "openai"
	gemini = "gemini"
