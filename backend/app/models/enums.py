from enum import Enum


class UserRole(str, Enum):
	citoyen = "citoyen"
	avocat = "avocat"
	juge = "juge"
	admin = "admin"


class DocumentSourceType(str, Enum):
	loi = "loi"
	jurisprudence = "jurisprudence"


class DocumentStatus(str, Enum):
	en_vigueur = "en_vigueur"
	modifie = "modifie"
	abroge = "abroge"
