import asyncio
import mimetypes
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from config import WORKSPACE_ROOT


async def _run_git(*args: str) -> str:
    from config import WORKSPACE_ROOT as _root
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(_root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"git error: {stderr.decode(errors='replace').strip()}"
    return stdout.decode(errors="replace")


def register(mcp: FastMCP) -> None:

    @mcp.resource("file://{path}")
    async def read_file_resource(path: str) -> str:
        """Read any file within the workspace as a resource."""
        resolved = (WORKSPACE_ROOT / path).resolve()
        if not resolved.is_relative_to(WORKSPACE_ROOT):
            raise ValueError(f"Path '{path}' is outside the workspace.")
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: '{path}'")

        mime, _ = mimetypes.guess_type(str(resolved))
        is_text = mime is None or mime.startswith("text/") or mime in {
            "application/json",
            "application/javascript",
            "application/xml",
        }
        if not is_text:
            return f"[binary file: {mime or 'unknown'}, {resolved.stat().st_size} bytes]"

        try:
            return resolved.read_text(encoding="utf-8", errors="replace")
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot read file: {e}") from e

    @mcp.resource("git://status")
    async def git_status_resource() -> str:
        """Current git working tree status as a resource."""
        output = await _run_git("status")
        return output

    @mcp.resource("git://log")
    async def git_log_resource() -> str:
        """Recent 20 commits as a resource."""
        output = await _run_git(
            "log",
            "--oneline",
            "--max-count=20",
            "--format=%H  %ad  %an  %s",
            "--date=short",
        )
        return output or "No commits found."
