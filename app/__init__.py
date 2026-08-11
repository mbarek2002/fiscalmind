"""Compatibility package to expose backend/app as top-level app imports.

This allows running commands from repository root while keeping existing imports
like `from app.main import app` valid.
"""

from pathlib import Path
import pkgutil

__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]
_backend_app_dir = Path(__file__).resolve().parent.parent / "backend" / "app"
if _backend_app_dir.exists():
	__path__.append(str(_backend_app_dir))
