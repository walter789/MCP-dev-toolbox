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
from tools import git_tools, file_tools, code_tools  # noqa: E402
from resources import handlers as resource_handlers   # noqa: E402
from prompts import templates as prompt_templates     # noqa: E402

git_tools.register(mcp)
file_tools.register(mcp)
code_tools.register(mcp)
resource_handlers.register(mcp)
prompt_templates.register(mcp)

if __name__ == "__main__":
    mcp.run()
