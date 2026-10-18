import os
import re
from dataclasses import dataclass
from pathlib import Path

from mcp_dev_toolbox.config import EXCLUDED_DIRS, WORKSPACE_ROOT

# File extensions treated as source code worth indexing
INDEXABLE_EXTENSIONS = {
    "py", "js", "ts", "jsx", "tsx", "java", "go", "rs", "cpp", "c",
    "h", "cs", "rb", "php", "swift", "kt", "scala", "sh", "yaml", "yml",
    "json", "toml", "md",
}

# Only these languages are split on def/function/class. Applying the pattern
# elsewhere (e.g. code samples inside Markdown) produced fake "functions".
DEFINITION_EXTENSIONS = {"py", "js", "ts", "jsx", "tsx", "mjs", "cjs"}
MARKDOWN_EXTENSIONS = {"md", "markdown"}

# Matches Python/JS/TS function and class definitions
_FN_PATTERN = re.compile(
    r"^(\s*)(async\s+def\s+|def\s+|function\s+|async\s+function\s+|class\s+)(\w+)"
)
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")

CHUNK_SIZE = 40       # lines per fallback block chunk
CHUNK_OVERLAP = 8     # lines of overlap between fallback chunks
MAX_CHUNK_LINES = 80  # longer chunks are split; huge chunks embed poorly


@dataclass
class CodeChunk:
    content: str
    file_path: str   # relative to WORKSPACE_ROOT, always with "/" separators
    start_line: int  # 1-indexed
    end_line: int
    chunk_type: str  # "function" | "class" | "section" | "block"
    name: str        # function/class name, section heading, or "" for blocks


def _make_chunks(lines: list[str], rel_path: str, start: int, end: int,
                 kind: str, name: str) -> list[CodeChunk]:
    """Build chunk(s) for lines[start:end], splitting anything over MAX_CHUNK_LINES."""
    chunks: list[CodeChunk] = []
    step = MAX_CHUNK_LINES - CHUNK_OVERLAP
    pos = start
    while pos < end:
        stop = min(pos + MAX_CHUNK_LINES, end)
        content = "\n".join(lines[pos:stop]).strip()
        if content:
            chunks.append(CodeChunk(
                content=content,
                file_path=rel_path,
                start_line=pos + 1,
                end_line=stop,
                chunk_type=kind,
                name=name,
            ))
        if stop >= end:
            break
        pos += step
    return chunks


def _chunk_by_definitions(lines: list[str], rel_path: str) -> list[CodeChunk]:
    """Split a file into per-function/class chunks using a line-start heuristic."""
    boundaries: list[tuple[int, str, str]] = []  # (line_idx, type, name)
    for i, line in enumerate(lines):
        m = _FN_PATTERN.match(line)
        if m:
            kind = "class" if "class " in m.group(2) else "function"
            boundaries.append((i, kind, m.group(3)))

    if not boundaries:
        return _chunk_by_blocks(lines, rel_path)

    chunks: list[CodeChunk] = []
    # Module header (imports, constants) before the first definition
    if boundaries[0][0] > 0:
        chunks.extend(_make_chunks(lines, rel_path, 0, boundaries[0][0], "block", ""))
    for idx, (start, kind, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        chunks.extend(_make_chunks(lines, rel_path, start, end, kind, name))
    return chunks


def _chunk_markdown(lines: list[str], rel_path: str) -> list[CodeChunk]:
    """Split Markdown into one chunk per heading section.

    Headings inside fenced code blocks are ignored, so code samples stay
    inside the section that contains them.
    """
    boundaries: list[tuple[int, str]] = []  # (line_idx, heading text)
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            m = _HEADING_PATTERN.match(line)
            if m:
                boundaries.append((i, m.group(2)))

    if not boundaries:
        return _chunk_by_blocks(lines, rel_path)

    chunks: list[CodeChunk] = []
    if boundaries[0][0] > 0:
        chunks.extend(_make_chunks(lines, rel_path, 0, boundaries[0][0], "section", ""))
    for idx, (start, heading) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        chunks.extend(_make_chunks(lines, rel_path, start, end, "section", heading))
    return chunks


def _chunk_by_blocks(lines: list[str], rel_path: str) -> list[CodeChunk]:
    """Fixed-size chunks with overlap for files without recognizable structure."""
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
        if i + CHUNK_SIZE >= len(lines):
            break
    return chunks


def chunk_file(lines: list[str], rel_path: str, ext: str) -> list[CodeChunk]:
    """Pick a chunking strategy based on file type."""
    if ext in MARKDOWN_EXTENSIONS:
        return _chunk_markdown(lines, rel_path)
    if ext in DEFINITION_EXTENSIONS:
        return _chunk_by_definitions(lines, rel_path)
    return _chunk_by_blocks(lines, rel_path)


def chunk_workspace(base_path: str = ".") -> list[CodeChunk]:
    """Walk the workspace and return all code chunks ready for embedding."""
    resolved = (WORKSPACE_ROOT / base_path).resolve()
    all_chunks: list[CodeChunk] = []

    for root, dirs, files in os.walk(resolved):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".mcp_")]
        for fname in files:
            ext = Path(fname).suffix.lstrip(".").lower()
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
            rel = fpath.relative_to(WORKSPACE_ROOT).as_posix()
            all_chunks.extend(chunk_file(lines, rel, ext))

    return all_chunks
