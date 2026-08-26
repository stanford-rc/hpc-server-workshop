"""
mcp_server.py — MCP server over Streamable HTTP (Tier 3).

Exposes a directory of documentation as MCP tools. Claude (Desktop or Code) on
your laptop connects through an SSH tunnel, discovers these tools, and decides
which to call based on your question — you never name an endpoint.

Where the model runs: not here. This process does file reads and string
matching, needs no GPU, and holds no model. Anthropic runs the model on the
client side. That separation is the whole point of MCP, and it's why this tier
is cheap to host. For a fully-local alternative, see "Keeping it all on
Sherlock" in README.md.

Transport is Streamable HTTP (the current MCP standard), which means this is
ordinary HTTP and forwards through exactly the same SSH tunnel as Tier 4.
The MCP endpoint is at /mcp.

Start manually:
  python mcp_server.py

Via SLURM:
  sbatch submit_server.sh
"""

import os
import socket
from pathlib import Path

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

BASE_DIR = Path(__file__).parent
DOCS_DIR = Path(os.environ.get("DOCS_DIR", BASE_DIR / "docs"))

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_mcp.txt"))
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")


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


def main():
    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")

    # DNS-rebinding protection is on by default and checks the Host header.
    # Through the tunnel the browser/client sends "localhost:<local port>",
    # which is NOT this server's own host — so it has to be allowed explicitly
    # or every request fails with "Invalid request host". The local port is
    # yours to choose, so allow the usual suspects plus $ALLOWED_HOSTS.
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
        f"MCP server on {BIND_HOST}:{PORT} (node {node})\n"
        f"Docs: {DOCS_DIR} ({len(list(DOCS_DIR.glob('*.md')))} files)\n"
        f"Address written to {ADDR_FILE}\n"
        f"From your laptop:\n"
        f"  ssh -NfL 8080:localhost:{PORT} {node}\n"
        f"  claude mcp add --transport http workshop-docs http://localhost:8080/mcp",
        flush=True,
    )

    uvicorn.run(app, host=BIND_HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
