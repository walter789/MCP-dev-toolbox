import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import EXCLUDED_DIRS, WORKSPACE_ROOT


def _should_skip(name: str) -> bool:
    return name in EXCLUDED_DIRS


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def count_lines_by_language(
        path: str = ".",
        exclude_blank: bool = True,
    ) -> str:
        """Return line-of-code breakdown grouped by file extension."""
        resolved = (WORKSPACE_ROOT / path).resolve()
        if not resolved.is_relative_to(WORKSPACE_ROOT):
            return f"Error: path '{path}' is outside the workspace."

        counts: dict[str, int] = defaultdict(int)
        file_counts: dict[str, int] = defaultdict(int)

        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if not _should_skip(d)]
            for fname in files:
                fpath = Path(root) / fname
                ext = fpath.suffix.lstrip(".") or "no-extension"
                try:
                    lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
                except (PermissionError, OSError):
                    continue
                if exclude_blank:
                    lines = [l for l in lines if l.strip()]
                counts[ext] += len(lines)
                file_counts[ext] += 1

        if not counts:
            return "No files found."

        rows = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        total = sum(counts.values())
        lines_out = [f"{'Extension':<18}  {'Files':>6}  {'Lines':>8}"]
        lines_out.append("-" * 38)
        for ext, lc in rows:
            lines_out.append(f"{ext:<18}  {file_counts[ext]:>6}  {lc:>8}")
        lines_out.append("-" * 38)
        lines_out.append(f"{'TOTAL':<18}  {sum(file_counts.values()):>6}  {total:>8}")
        return "\n".join(lines_out)

    @mcp.tool()
    async def find_long_functions(
        file_path: str,
        threshold: int = 50,
    ) -> str:
        """Find functions longer than `threshold` lines. Works for Python and JavaScript/TypeScript."""
        resolved = (WORKSPACE_ROOT / file_path).resolve()
        if not resolved.is_relative_to(WORKSPACE_ROOT):
            return f"Error: path '{file_path}' is outside the workspace."
        if not resolved.is_file():
            return f"Error: '{file_path}' does not exist."

        try:
            source = resolved.read_text(encoding="utf-8", errors="replace")
        except (PermissionError, OSError) as e:
            return f"Error reading file: {e}"

        lines = source.splitlines()
        # Heuristic: match Python `def`/`async def` or JS/TS `function`
        fn_pattern = re.compile(
            r"^\s*(async\s+def\s+|def\s+|function\s+|async\s+function\s+)(\w+)"
        )
        results: list[str] = []
        fn_starts: list[tuple[int, str, int]] = []  # (line_idx, name, indent)

        for i, line in enumerate(lines):
            m = fn_pattern.match(line)
            if m:
                indent = len(line) - len(line.lstrip())
                fn_starts.append((i, m.group(2), indent))

        for idx, (start_i, name, base_indent) in enumerate(fn_starts):
            if idx + 1 < len(fn_starts):
                # Find next function at same or lower indent level
                end_i = fn_starts[idx + 1][0]
                for j in range(idx + 1, len(fn_starts)):
                    if fn_starts[j][2] <= base_indent:
                        end_i = fn_starts[j][0]
                        break
            else:
                end_i = len(lines)

            length = end_i - start_i
            if length > threshold:
                results.append(
                    f"Line {start_i + 1}: {name}()  —  {length} lines"
                )

        if not results:
            return f"No functions longer than {threshold} lines found in '{file_path}'."
        return f"Functions exceeding {threshold} lines in '{file_path}':\n" + "\n".join(results)
