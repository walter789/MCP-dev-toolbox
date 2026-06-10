import os
import re
from dataclasses import dataclass
from pathlib import Path

from config import EXCLUDED_DIRS, WORKSPACE_ROOT

# File extensions treated as source code worth indexing
INDEXABLE_EXTENSIONS = {
    "py", "js", "ts", "jsx", "tsx", "java", "go", "rs", "cpp", "c",
    "h", "cs", "rb", "php", "swift", "kt", "scala", "sh", "yaml", "yml",
    "json", "toml", "md",
}

# Matches Python/JS/TS function and class definitions
_FN_PATTERN = re.compile(
    r"^(\s*)(async\s+def\s+|def\s+|function\s+|async\s+function\s+|class\s+)(\w+)"
)

CHUNK_SIZE = 40      # lines per fallback block chunk
CHUNK_OVERLAP = 8   # lines of overlap between fallback chunks


@dataclass
class CodeChunk:
    content: str
    file_path: str   # relative to WORKSPACE_ROOT
    start_line: int  # 1-indexed
    end_line: int
    chunk_type: str  # "function" | "class" | "block"
    name: str        # function/class name, or "" for blocks


def _chunk_by_definitions(lines: list[str], rel_path: str) -> list[CodeChunk]:
    """Split a file into per-function/class chunks using indentation heuristic."""
    boundaries: list[tuple[int, str, str]] = []  # (line_idx, type, name)
    for i, line in enumerate(lines):
        m = _FN_PATTERN.match(line)
        if m:
            kind = "class" if "class " in m.group(2) else "function"
            boundaries.append((i, kind, m.group(3)))

    if not boundaries:
        return _chunk_by_blocks(lines, rel_path)

    chunks: list[CodeChunk] = []
    for idx, (start, kind, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        if content:
            chunks.append(CodeChunk(
                content=content,
                file_path=rel_path,
                start_line=start + 1,
                end_line=end,
                chunk_type=kind,
                name=name,
            ))
    return chunks


def _chunk_by_blocks(lines: list[str], rel_path: str) -> list[CodeChunk]:
    """Fixed-size chunks with overlap for files without recognizable definitions."""
    chunks: list[CodeChunk] = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i in range(0, len(lines), step):
        block = lines[i: i + CHUNK_SIZE]
        content = "\n".join(block).strip()
        if content:
            chunks.append(CodeChunk(
                content=content,
                file_path=rel_path,
                start_line=i + 1,
                end_line=min(i + CHUNK_SIZE, len(lines)),
                chunk_type="block",
                name="",
            ))
    return chunks


def chunk_workspace(base_path: str = ".") -> list[CodeChunk]:
    """Walk the workspace and return all code chunks ready for embedding."""
    resolved = (WORKSPACE_ROOT / base_path).resolve()
    all_chunks: list[CodeChunk] = []

    for root, dirs, files in os.walk(resolved):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".mcp_")]
        for fname in files:
            ext = Path(fname).suffix.lstrip(".")
            if ext not in INDEXABLE_EXTENSIONS:
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except (PermissionError, OSError):
                continue
            lines = text.splitlines()
            if not lines:
                continue
            rel = str(fpath.relative_to(WORKSPACE_ROOT))
            chunks = _chunk_by_definitions(lines, rel)
            all_chunks.extend(chunks)

    return all_chunks
