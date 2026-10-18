from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from the current directory, then from a source checkout's root
# (the folder containing server.py). Existing environment variables win.
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_raw_root = os.getenv("WORKSPACE_ROOT", str(Path.cwd()))
WORKSPACE_ROOT: Path = Path(_raw_root).resolve()

_raw_excluded = os.getenv(
    "EXCLUDED_DIRS",
    ".git,__pycache__,.venv,venv,node_modules,.mypy_cache,.pytest_cache",
)
EXCLUDED_DIRS: list[str] = [d.strip() for d in _raw_excluded.split(",") if d.strip()]
