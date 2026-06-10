from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent


def _user(text: str) -> PromptMessage:
    return PromptMessage(role="user", content=TextContent(type="text", text=text))


def register(mcp: FastMCP) -> None:

    @mcp.prompt()
    def code_review(file_path: str, focus_area: str = "general") -> list[PromptMessage]:
        """Structured code review for a given file."""
        return [
            _user(
                f"Please review the file `{file_path}` with focus on: {focus_area}.\n\n"
                "Structure your review as:\n"
                "1. **Summary** — what the code does\n"
                "2. **Issues** — bugs, security risks, edge cases (be specific, cite line numbers)\n"
                "3. **Improvements** — readability, performance, design\n"
                "4. **Verdict** — overall quality rating (1–5) with one-line justification\n\n"
                f"Use the `file://{file_path}` resource to read the file before reviewing."
            )
        ]

    @mcp.prompt()
    def commit_message(diff_summary: str) -> list[PromptMessage]:
        """Generate a conventional commit message from a diff summary."""
        return [
            _user(
                "Write a git commit message following the Conventional Commits spec "
                "(https://www.conventionalcommits.org/) for the following change:\n\n"
                f"{diff_summary}\n\n"
                "Format:\n"
                "<type>(<optional scope>): <short imperative summary>\n\n"
                "<body — what changed and why, wrapped at 72 chars>\n\n"
                "Types: feat | fix | refactor | docs | test | chore | perf | ci\n"
                "Keep the subject line under 72 characters."
            )
        ]

    @mcp.prompt()
    def explain_codebase(entry_point: str) -> list[PromptMessage]:
        """Generate an onboarding guide starting from an entry point file."""
        return [
            _user(
                f"I'm new to this codebase. Starting from `{entry_point}`, help me understand it.\n\n"
                "Please cover:\n"
                "1. **Purpose** — what problem does this project solve?\n"
                "2. **Architecture** — high-level structure and key modules\n"
                "3. **Entry point walkthrough** — trace the execution flow from `{entry_point}`\n"
                "4. **Key concepts** — domain terms or patterns I need to know\n"
                "5. **Where to start** — which files to read first as a new contributor\n\n"
                f"Use `file://{entry_point}` and related resources to inform your explanation."
            )
        ]

    @mcp.prompt()
    def debug_guide(error_message: str, file_path: str = "") -> list[PromptMessage]:
        """Systematic debugging template for a given error."""
        file_context = (
            f" The error occurs in or near `{file_path}`." if file_path else ""
        )
        return [
            _user(
                f"I'm seeing this error:{file_context}\n\n"
                f"```\n{error_message}\n```\n\n"
                "Help me debug it systematically:\n"
                "1. **Diagnosis** — what is this error telling us?\n"
                "2. **Root causes** — list the 2–3 most likely causes\n"
                "3. **Investigation steps** — concrete commands or code to confirm the cause\n"
                "4. **Fix** — recommended solution with code snippet if applicable\n"
                "5. **Prevention** — how to avoid this class of bug in future\n"
                + (
                    f"\nUse `file://{file_path}` to read the relevant source." if file_path else ""
                )
            )
        ]
