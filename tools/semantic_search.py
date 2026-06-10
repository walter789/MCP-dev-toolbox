from mcp.server.fastmcp import FastMCP

from indexer import embedder


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def build_index(path: str = ".") -> str:
        """Build the semantic search index for the workspace.
        Must be run once before using semantic_search.
        Re-run after adding or changing files.
        """
        result = embedder.build_index(path)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        return (
            f"Index built successfully.\n"
            f"  Chunks embedded : {result['chunks']}\n"
            f"  Model           : {result['model']}\n"
            f"  Time taken      : {result['embed_seconds']}s"
        )

    @mcp.tool()
    async def semantic_search(query: str, top_k: int = 5) -> str:
        """Search the codebase using natural language.
        Finds code by meaning, not just keywords.
        Example queries: 'user authentication logic', 'database connection setup',
        'error handling in API calls'.
        Run build_index first if you haven't already.
        """
        results = embedder.search(query, top_k=top_k)
        if not results:
            return (
                "No index found. Run the build_index tool first, "
                "then retry your search."
            )

        lines = [f"Top {len(results)} results for: '{query}'\n"]
        for i, r in enumerate(results, 1):
            name_label = f"  {r['name']}()" if r["name"] else ""
            lines.append(
                f"[{i}] {r['file']}:{r['start_line']}-{r['end_line']}"
                f"  ({r['type']}{name_label})  score={r['score']}"
            )
            lines.append(f"    {r['snippet'][:200].replace(chr(10), ' ')}")
            lines.append("")
        return "\n".join(lines)
