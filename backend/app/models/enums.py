from enum import Enum


class UserRole(str, Enum):
	citoyen = "citoyen"
	avocat = "avocat"
	juge = "juge"
	admin = "admin"
	entreprise = "entreprise"


class DocumentSourceType(str, Enum):
	loi = "loi"
	jurisprudence = "jurisprudence"


class DocumentStatus(str, Enum):
	en_vigueur = "en_vigueur"
	modifie = "modifie"
	abroge = "abroge"


class IngestionStatus(str, Enum):
	uploaded = "uploaded"
	processing = "processing"
	indexed = "indexed"
	failed = "failed"


class FinancialSourceType(str, Enum):
	document = "document"
	formulaire = "formulaire"
	texte_libre = "texte_libre"
	mixte = "mixte"


class FinancialSubmissionStatus(str, Enum):
	pending = "pending"
	analyzing = "analyzing"
	completed = "completed"
	failed = "failed"


class FinancialDocumentStatus(str, Enum):
	uploaded = "uploaded"
	processing = "processing"
	extracted = "extracted"
	failed = "failed"


class CitationType(str, Enum):
	article = "article"
	jurisprudence = "jurisprudence"
