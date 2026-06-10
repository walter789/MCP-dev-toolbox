import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "dev-toolbox",
    instructions=(
        "A developer utility server for analyzing local codebases. "
        "Provides git history, file inspection, code search, and structured prompt templates."
    ),
)

# Tools, resources, and prompts are registered by importing their modules.
# Each module calls register(mcp) to attach its handlers.
from tools import git_tools, file_tools, code_tools, semantic_search  # noqa: E402
from resources import handlers as resource_handlers                    # noqa: E402
from prompts import templates as prompt_templates                      # noqa: E402

git_tools.register(mcp)
file_tools.register(mcp)
code_tools.register(mcp)
semantic_search.register(mcp)
resource_handlers.register(mcp)
prompt_templates.register(mcp)

if __name__ == "__main__":
    transport = os.getenv("TRANSPORT", "stdio")
    if transport == "sse":
        # HTTP/SSE mode — used when deployed to a cloud host (Railway, Render, etc.)
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio mode — used for local Claude Desktop / Cursor integration
        mcp.run(transport="stdio")
