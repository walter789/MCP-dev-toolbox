"""Tests for indexer.chunker. Run with: python -m pytest"""
from mcp_dev_toolbox.indexer.chunker import MAX_CHUNK_LINES, chunk_file, chunk_workspace


def test_markdown_splits_by_heading_not_by_code_samples():
    md = [
        "# Title",
        "Intro text.",
        "## Usage",
        "```python",
        "def _run_git(*args):",
        "    # not a heading, not a real function",
        "    pass",
        "```",
        "## License",
        "MIT",
    ]
    chunks = chunk_file(md, "README.md", "md")
    assert [c.name for c in chunks] == ["Title", "Usage", "License"]
    assert all(c.chunk_type == "section" for c in chunks)
    # the fenced def stays inside the Usage section
    assert "def _run_git" in chunks[1].content


def test_python_definitions_and_module_header():
    py = ["import os", "X = 1", "", "def a():", "    return 1", "", "class B:", "    pass"]
    chunks = chunk_file(py, "pkg/mod.py", "py")
    assert [(c.chunk_type, c.name) for c in chunks] == [
        ("block", ""), ("function", "a"), ("class", "B"),
    ]


def test_long_chunks_are_capped():
    body = ["def big():"] + [f"    x{i} = {i}" for i in range(300)]
    chunks = chunk_file(body, "big.py", "py")
    assert len(chunks) > 1
    assert all(c.end_line - c.start_line + 1 <= MAX_CHUNK_LINES for c in chunks)
    assert all(c.name == "big" for c in chunks)


def test_non_definition_languages_use_blocks():
    go = ["package main", "func main() {", "}"]
    chunks = chunk_file(go, "main.go", "go")
    assert [c.chunk_type for c in chunks] == ["block"]


def test_workspace_paths_use_forward_slashes():
    chunks = chunk_workspace("mcp_dev_toolbox/indexer")
    assert chunks, "expected the indexer package to be indexed"
    assert all("\\" not in c.file_path for c in chunks)
    assert any(c.file_path == "mcp_dev_toolbox/indexer/chunker.py" for c in chunks)
