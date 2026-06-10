from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from the project directory regardless of where Python was launched from
load_dotenv(Path(__file__).parent / ".env")

_raw_root = os.getenv("WORKSPACE_ROOT", str(Path.cwd()))
WORKSPACE_ROOT: Path = Path(_raw_root).resolve()

_raw_excluded = os.getenv(
    "EXCLUDED_DIRS",
    ".git,__pycache__,.venv,venv,node_modules,.mypy_cache,.pytest_cache",
)
EXCLUDED_DIRS: list[str] = [d.strip() for d in _raw_excluded.split(",") if d.strip()]
