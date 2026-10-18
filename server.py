"""Run the server from a source checkout: `python server.py`.

Kept so existing client configs that point at server.py keep working.
Installed users can run the `mcp-dev-toolbox` command instead.
"""
from mcp_dev_toolbox.server import main

if __name__ == "__main__":
    main()
