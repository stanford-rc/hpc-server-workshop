"""
mcp_server.py — MCP server over Streamable HTTP (Tier 3).

Offers a folder of documentation as three MCP tools. Claude Code connects,
sees the tools, and decides which to call to answer your question.

The model doesn't run here: this server only reads files and searches their
text, so it needs no GPU. The model runs at Anthropic, behind Claude Code.

The MCP address is /mcp. Every request must include the token from TOKEN_FILE
(see Tier 1).

Start it:
  bash submit_server.sh      # inside an sh_dev session
  sbatch submit_server.sh    # or as a batch job
"""

import os
import secrets
import socket
from pathlib import Path

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import PlainTextResponse

BASE_DIR = Path(__file__).parent
DOCS_DIR = Path(os.environ.get("DOCS_DIR", BASE_DIR / "docs"))

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_mcp.txt"))
# 0.0.0.0 = accept connections from any machine on Sherlock; the token keeps
# everyone else out.
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))


def pick_port() -> int:
    """Return $PORT if set, else an unused ephemeral port (same as Tier 4)."""
    override = os.environ.get("PORT")
    if override:
        return int(override)
    with socket.socket() as probe:
        probe.bind(("", 0))
        return probe.getsockname()[1]


PORT = pick_port()

mcp = MCPServer(
    "srcc-workshop-docs",
    instructions=(
        "Cluster documentation for a Stanford Research Computing workshop. "
        "Use list_docs to see what is available, search_docs to find which "
        "document covers a topic, and read_doc to read one in full. Prefer "
        "search_docs before read_doc when you don't know the filename."
    ),
)


def _safe_doc(filename: str) -> Path:
    """Resolve a filename to a path inside DOCS_DIR, or raise.

    Tool arguments come from a model, which means they are effectively
    untrusted input. Without this, "../../etc/passwd" would be readable.
    """
    name = os.path.basename(filename or "")
    if not name or not name.endswith(".md"):
        raise ValueError(f"Not a documentation file: {filename!r}")
    path = DOCS_DIR / name
    if not path.is_file():
        available = ", ".join(sorted(p.name for p in DOCS_DIR.glob("*.md")))
        raise ValueError(f"No such doc: {name}. Available: {available}")
    return path


@mcp.tool()
def list_docs() -> list[str]:
    """List the available cluster documentation files."""
    return sorted(p.name for p in DOCS_DIR.glob("*.md"))


@mcp.tool()
def read_doc(filename: str) -> str:
    """Read one documentation file in full.

    Args:
        filename: A filename from list_docs, e.g. "storage.md".
    """
    return _safe_doc(filename).read_text()


@mcp.tool()
def search_docs(query: str) -> list[dict]:
    """Find which documents mention a term, with matching lines.

    Case-insensitive substring search — deliberately simple. The production
    SRCC server uses BM25 + FAISS instead; swapping this one function is
    where you'd plug real retrieval in.

    Args:
        query: A word or phrase to look for, e.g. "quota" or "out of memory".
    """
    needle = query.lower().strip()
    if not needle:
        return []

    hits = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        matches = [
            line.strip()
            for line in path.read_text().splitlines()
            if needle in line.lower()
        ]
        if matches:
            hits.append({
                "filename": path.name,
                "match_count": len(matches),
                "matches": matches[:5],
            })
    return hits


class RequireToken:
    """Refuse any request that doesn't carry the token in an "x-token" header."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            given = dict(scope["headers"]).get(b"x-token", b"").decode()
            if not secrets.compare_digest(given, self.token):
                await PlainTextResponse("Missing or wrong token", status_code=401)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def main():
    if not TOKEN_FILE.exists():
        raise SystemExit(f"No token file at {TOKEN_FILE}. Make one first (see the Tier 1 README).")
    token = TOKEN_FILE.read_text().strip()

    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")

    # The MCP library only answers requests addressed to names it knows. Through
    # the tunnel, requests arrive addressed to "localhost:<your laptop's port>",
    # so list the common laptop ports here; add others with $ALLOWED_HOSTS.
    extra = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]
    allowed = [
        "localhost", "127.0.0.1",
        f"localhost:{PORT}", f"127.0.0.1:{PORT}",
        f"{node}:{PORT}",
        *(f"localhost:{p}" for p in (8080, 8081, 8000, 3000)),
        *extra,
    ]

    app = mcp.streamable_http_app(
        transport_security=TransportSecuritySettings(allowed_hosts=allowed)
    )

    print(
        f"MCP server on {node}:{PORT}\n"
        f"Docs: {DOCS_DIR} ({len(list(DOCS_DIR.glob('*.md')))} files)\n"
        f"Address written to {ADDR_FILE}\n"
        f"To connect Claude Code, see step 2 in README.md.",
        flush=True,
    )

    uvicorn.run(RequireToken(app, token), host=BIND_HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
