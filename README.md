# mcp-dev-toolbox

A developer utility MCP server that exposes git analysis, file inspection, and code search capabilities to any MCP client (Claude Desktop, Cursor, etc.).

---

## Features

| Primitive | Count | What's included |
|-----------|-------|-----------------|
| **Tools** | 10 | Git history, diffs, blame · File search, TODO finder, stats · LOC counter, long-function detector |
| **Resources** | 3 | `file://{path}` · `git://status` · `git://log` |
| **Prompts** | 4 | Code review · Commit message · Explain codebase · Debug guide |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/mcp-dev-toolbox.git
cd mcp-dev-toolbox
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
WORKSPACE_ROOT=/absolute/path/to/your/project
EXCLUDED_DIRS=.git,__pycache__,.venv,node_modules
```

`WORKSPACE_ROOT` is the codebase you want to analyze. All tools operate within this boundary — paths outside it are rejected.

### 3. Add to Claude Desktop

Open your Claude Desktop config (`claude_desktop_config.json`) and add:

```json
{
  "mcpServers": {
    "dev-toolbox": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-dev-toolbox/server.py"],
      "env": {
        "WORKSPACE_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

Restart Claude Desktop. You'll see the toolbox icon appear in the toolbar.

---

## Tools Reference

### Git Tools

| Tool | Description | Key Args |
|------|-------------|----------|
| `git_log` | Recent commits with hash, author, date, message | `max_count`, `since_days` |
| `git_status` | Working tree status (modified / staged / untracked) | — |
| `git_diff` | Diff for a file or all staged changes | `file_path`, `staged` |
| `git_blame` | Last modifier per line | `file_path`, `start_line`, `end_line` |

### File Tools

| Tool | Description | Key Args |
|------|-------------|----------|
| `find_todos` | Search for TODO/FIXME/HACK/NOTE comments | `path`, `extensions` |
| `search_in_files` | Regex search across source files | `pattern`, `path`, `extensions`, `case_sensitive` |
| `get_file_stats` | Size, line count, encoding, last modified | `file_path` |
| `list_recent_files` | Files modified in the last N days | `days`, `extensions`, `path` |

### Code Tools

| Tool | Description | Key Args |
|------|-------------|----------|
| `count_lines_by_language` | LOC breakdown by file extension | `path`, `exclude_blank` |
| `find_long_functions` | Detect functions exceeding a line threshold | `file_path`, `threshold` |

---

## Resources Reference

| URI | Description |
|-----|-------------|
| `file://{path}` | Read any workspace file as a resource |
| `git://status` | Current `git status` output |
| `git://log` | Last 20 commits |

---

## Prompts Reference

| Prompt | Description | Args |
|--------|-------------|------|
| `code_review` | Structured code review | `file_path`, `focus_area` |
| `commit_message` | Conventional commit from a diff summary | `diff_summary` |
| `explain_codebase` | Onboarding walkthrough from an entry point | `entry_point` |
| `debug_guide` | Systematic debugging template | `error_message`, `file_path` |

---

## Example Conversations

**"Show me what changed this week"**
> Claude calls `git_log(since_days=7)` and summarizes the commits.

**"Find all TODO comments in the src/ folder"**
> Claude calls `find_todos(path="src", extensions=["py"])`.

**"What's the largest file by line count?"**
> Claude calls `count_lines_by_language()` then `get_file_stats()` on the top result.

**"Review my authentication module"**
> Claude uses the `code_review` prompt → reads `file://src/auth.py` → returns structured review.

**"Write a commit message for my staged changes"**
> Claude calls `git_diff(staged=True)` then uses the `commit_message` prompt.

---

## Security

- All file operations validate that the resolved path is within `WORKSPACE_ROOT` before reading.
- Git subprocess calls run in `WORKSPACE_ROOT` with no shell interpolation (`create_subprocess_exec`, not `shell=True`).
- Binary files are detected and skipped rather than returned as garbled text.

---

## Project Structure

```
mcp-dev-toolbox/
├── server.py              # FastMCP entry point — wires all modules
├── config.py              # Loads .env, exposes WORKSPACE_ROOT + EXCLUDED_DIRS
├── tools/
│   ├── git_tools.py       # 4 git tools (async subprocess)
│   ├── file_tools.py      # 4 file analysis tools
│   └── code_tools.py      # 2 code analysis tools
├── resources/
│   └── handlers.py        # 3 resource handlers
├── prompts/
│   └── templates.py       # 4 prompt templates
├── requirements.txt
└── .env.example
```
