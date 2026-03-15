"""Second Brain MCP server — FastMCP stdio transport."""
import sys
import threading
from fastmcp import FastMCP

mcp = FastMCP("second-brain")

# Token store for two-step destructive confirmation
_pending: dict[str, float] = {}
_pending_lock = threading.Lock()


@mcp.tool()
def sb_search(query: str, mode: str = "hybrid", limit: int = 10) -> list[dict]:
    """Search brain notes by keyword, semantic, or hybrid mode."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_capture(title: str, body: str, note_type: str = "note",
               tags: list[str] | None = None, sensitivity: str = "public") -> dict:
    """Capture a new note. Idempotent — identical title+body returns existing note."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_read(path: str) -> dict:
    """Read a note by absolute path."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_edit(path: str, body: str) -> dict:
    """Edit an existing note's body. Writes atomically."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_recap(name: str | None = None) -> str:
    """Get session recap or cross-context synthesis for a person/project name."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_digest() -> dict:
    """Generate or return the latest weekly digest."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_connections(path: str) -> list[dict]:
    """Return notes connected to the given note path."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_actions(done: bool = False) -> list[dict]:
    """List action items. done=True lists completed items."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_actions_done(action_id: int) -> dict:
    """Mark an action item as complete by ID."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_files(subfolder: str | None = None) -> list[dict]:
    """List binary files in the brain, optionally filtered by subfolder."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_forget(slug: str, confirm_token: str = "") -> dict:
    """Forget a person. Call once to get confirmation token; call again with token within 60s."""
    raise NotImplementedError("stub")


@mcp.tool()
def sb_anonymize(path: str, confirm_token: str = "") -> dict:
    """Anonymize a note. Call once to get confirmation token; call again with token within 60s."""
    raise NotImplementedError("stub")


def main() -> None:
    mcp.run(transport="stdio")
