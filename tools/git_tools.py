import asyncio
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import WORKSPACE_ROOT


async def _run_git(*args: str, cwd: Optional[Path] = None) -> tuple[str, str, int]:
    # Import inside function to always read the live value, not a captured default
    from config import WORKSPACE_ROOT as _root
    work_dir = cwd or _root
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def git_log(max_count: int = 10, since_days: Optional[int] = None) -> str:
        """Return recent commits with hash, author, date, and message."""
        args = [
            "log",
            f"--max-count={max_count}",
            "--format=%H|%an|%ad|%s",
            "--date=short",
        ]
        if since_days is not None:
            args.append(f"--since={since_days} days ago")
        stdout, stderr, code = await _run_git(*args)
        if code != 0:
            return f"Error running git log: {stderr.strip()}"
        lines = [line for line in stdout.strip().splitlines() if line]
        if not lines:
            return "No commits found."
        rows = []
        for line in lines:
            parts = line.split("|", 3)
            if len(parts) == 4:
                rows.append(f"{parts[0][:8]}  {parts[2]}  {parts[1]:<20}  {parts[3]}")
        return "\n".join(rows)

    @mcp.tool()
    async def git_status() -> str:
        """Return working tree status — modified, staged, and untracked files."""
        stdout, stderr, code = await _run_git("status", "--porcelain")
        if code != 0:
            return f"Error running git status: {stderr.strip()}"
        return stdout.strip() or "Working tree is clean."

    @mcp.tool()
    async def git_diff(file_path: Optional[str] = None, staged: bool = False) -> str:
        """Return diff for a specific file or all changes. Set staged=True for staged diff."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            resolved = (WORKSPACE_ROOT / file_path).resolve()
            if not resolved.is_relative_to(WORKSPACE_ROOT):
                return f"Error: path '{file_path}' is outside the workspace."
            args.append(str(resolved))
        stdout, stderr, code = await _run_git(*args)
        if code != 0:
            return f"Error running git diff: {stderr.strip()}"
        return stdout.strip() or "No differences found."

    @mcp.tool()
    async def git_blame(
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """Show which commit last modified each line of a file."""
        resolved = (WORKSPACE_ROOT / file_path).resolve()
        if not resolved.is_relative_to(WORKSPACE_ROOT):
            return f"Error: path '{file_path}' is outside the workspace."
        if not resolved.is_file():
            return f"Error: '{file_path}' does not exist."
        args = ["blame", "--date=short"]
        if start_line is not None and end_line is not None:
            args += ["-L", f"{start_line},{end_line}"]
        args.append(str(resolved))
        stdout, stderr, code = await _run_git(*args)
        if code != 0:
            return f"Error running git blame: {stderr.strip()}"
        return stdout.strip()
