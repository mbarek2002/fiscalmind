from backend.app.db.session import Base, engine
from backend.app.models import db_models  # noqa: F401


async def init_db() -> None:
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
