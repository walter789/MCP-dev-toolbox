import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import EXCLUDED_DIRS, WORKSPACE_ROOT


def _resolve_safe(rel_path: str) -> tuple[Path, str | None]:
    """Resolve rel_path within WORKSPACE_ROOT. Returns (path, error_message)."""
    resolved = (WORKSPACE_ROOT / rel_path).resolve()
    if not resolved.is_relative_to(WORKSPACE_ROOT):
        return resolved, f"Error: path '{rel_path}' is outside the workspace."
    return resolved, None


def _should_skip(name: str) -> bool:
    return name in EXCLUDED_DIRS


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def find_todos(
        path: str = ".",
        extensions: Optional[list[str]] = None,
    ) -> str:
        """Search for TODO, FIXME, HACK, and NOTE comments across source files."""
        base, err = _resolve_safe(path)
        if err:
            return err
        pattern = re.compile(r"\b(TODO|FIXME|HACK|NOTE)\b[:\s]*(.*)", re.IGNORECASE)
        allowed_ext = {e.lstrip(".") for e in extensions} if extensions else None
        results: list[str] = []

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not _should_skip(d)]
            for fname in files:
                if allowed_ext and Path(fname).suffix.lstrip(".") not in allowed_ext:
                    continue
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except (PermissionError, OSError):
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    m = pattern.search(line)
                    if m:
                        rel = fpath.relative_to(WORKSPACE_ROOT)
                        results.append(f"{rel}:{i}  [{m.group(1)}] {m.group(2).strip()}")

        return "\n".join(results) if results else "No TODO/FIXME/HACK/NOTE comments found."

    @mcp.tool()
    async def search_in_files(
        pattern: str,
        path: str = ".",
        extensions: Optional[list[str]] = None,
        case_sensitive: bool = False,
    ) -> str:
        """Search for a regex pattern across files. Returns matching lines with file:line context."""
        base, err = _resolve_safe(path)
        if err:
            return err
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: invalid regex pattern — {e}"
        allowed_ext = {e.lstrip(".") for e in extensions} if extensions else None
        results: list[str] = []

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not _should_skip(d)]
            for fname in files:
                if allowed_ext and Path(fname).suffix.lstrip(".") not in allowed_ext:
                    continue
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except (PermissionError, OSError):
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        rel = fpath.relative_to(WORKSPACE_ROOT)
                        results.append(f"{rel}:{i}: {line.rstrip()}")
                        if len(results) >= 200:
                            results.append("... (truncated at 200 matches)")
                            return "\n".join(results)

        return "\n".join(results) if results else f"No matches found for pattern: {pattern!r}"

    @mcp.tool()
    async def get_file_stats(file_path: str) -> str:
        """Return file metadata: size, line count, last modified timestamp, and encoding hint."""
        resolved, err = _resolve_safe(file_path)
        if err:
            return err
        if not resolved.is_file():
            return f"Error: '{file_path}' does not exist or is not a file."
        try:
            stat = resolved.stat()
            raw = resolved.read_bytes()
        except (PermissionError, OSError) as e:
            return f"Error reading file: {e}"

        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
                encoding = "latin-1"
            except UnicodeDecodeError:
                return (
                    f"file: {file_path}\n"
                    f"size: {size_kb:.1f} KB\n"
                    f"encoding: binary (cannot count lines)\n"
                    f"last modified: {modified}"
                )

        line_count = len(text.splitlines())
        return (
            f"file: {file_path}\n"
            f"size: {size_kb:.1f} KB\n"
            f"lines: {line_count}\n"
            f"encoding: {encoding}\n"
            f"last modified: {modified}"
        )

    @mcp.tool()
    async def list_recent_files(
        days: int = 7,
        extensions: Optional[list[str]] = None,
        path: str = ".",
    ) -> str:
        """List files modified in the last N days, sorted by most recently modified."""
        base, err = _resolve_safe(path)
        if err:
            return err
        allowed_ext = {e.lstrip(".") for e in extensions} if extensions else None
        cutoff = datetime.now(tz=timezone.utc).timestamp() - days * 86400
        found: list[tuple[float, Path]] = []

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not _should_skip(d)]
            for fname in files:
                if allowed_ext and Path(fname).suffix.lstrip(".") not in allowed_ext:
                    continue
                fpath = Path(root) / fname
                try:
                    mtime = fpath.stat().st_mtime
                except OSError:
                    continue
                if mtime >= cutoff:
                    found.append((mtime, fpath))

        if not found:
            return f"No files modified in the last {days} day(s)."

        found.sort(reverse=True)
        lines = []
        for mtime, fpath in found:
            ts = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            rel = fpath.relative_to(WORKSPACE_ROOT)
            lines.append(f"{ts}  {rel}")
        return "\n".join(lines)
