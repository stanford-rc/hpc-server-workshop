"""
server.py — Web GUI server (Tier 4).

Serves a small web page *and* the JSON/file API it calls, from one FastAPI app
on a compute node. You reach it from a browser on your laptop through an SSH
tunnel; the page can read job results and move files in both directions.

The single most important design choice here: the HTML is served by the same
server that serves the API. The browser's origin and the fetch target are both
http://localhost:<LOCAL_PORT>, so there is no CORS configuration, no second
web server, and no frontend build step. Splitting them is what makes this hard.

Port selection follows the Sherlock Ollama doc pattern: bind an ephemeral port
so two people on the same node don't collide, then write "<node>:<port>" to a
known file so the tunnel command can be built from it.
  https://www.sherlock.stanford.edu/docs/software/using/ollama/

Any machine on Sherlock can connect, so everything except the page itself
needs the token from TOKEN_FILE (see Tier 1), sent either as an "x-token"
header or as an "x-token" cookie. The page has a box that sets the cookie,
which is what makes its plain download links work.

From your laptop:  ssh -N -L 8080:<machine>:<port> login.sherlock.stanford.edu
then open http://localhost:8080

Start it:
  bash submit_server.sh      # inside an sh_dev session
  sbatch submit_server.sh    # or as a batch job
"""

import os
import secrets
import shutil
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security, UploadFile
from fastapi.security import APIKeyCookie, APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", BASE_DIR / "results"))
INPUTS_DIR = Path(os.environ.get("INPUTS_DIR", BASE_DIR / "inputs"))

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_gui.txt"))
# 0.0.0.0 = accept connections from any machine on Sherlock; the token keeps
# everyone else out.
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))
if not TOKEN_FILE.exists():
    raise SystemExit(f"No token file at {TOKEN_FILE}. Make one first (see the Tier 1 README).")
TOKEN = TOKEN_FILE.read_text().strip()

token_header = APIKeyHeader(name="x-token", auto_error=False)
token_cookie = APIKeyCookie(name="x-token", auto_error=False)


def require_token(
    from_header: str | None = Security(token_header),
    from_cookie: str | None = Security(token_cookie),
):
    given = from_header or from_cookie
    if not given or not secrets.compare_digest(given, TOKEN):
        raise HTTPException(status_code=401, detail="Missing or wrong token")


def pick_port() -> int:
    """Return $PORT if set, else an unused ephemeral port.

    Binding to port 0 lets the OS pick a free one. There is a small race
    between closing this socket and uvicorn binding it, which is fine here —
    on a shared node it beats a hardcoded port that a neighbor already holds.
    """
    override = os.environ.get("PORT")
    if override:
        return int(override)
    with socket.socket() as probe:
        probe.bind(("", 0))
        return probe.getsockname()[1]


PORT = pick_port()


def safe_name(filename: str) -> str:
    """Reduce a client-supplied filename to a bare name inside our directory.

    Filenames come from the browser. Without this check, a name like
    "../../.ssh/authorized_keys" would read or write outside the intended folder.
    """
    name = os.path.basename(filename or "")
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {filename!r}")
    return name


@asynccontextmanager
async def lifespan(app: FastAPI):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # "<machine>:<port>", the same format as the other tiers.
    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")

    # flush=True so the lines show up right away in a batch job's log file.
    print(
        f"Web server on {node}:{PORT}\n"
        f"Address written to {ADDR_FILE}\n"
        f"On your laptop, open the tunnel (leave it running):\n"
        f"  ssh -N -L 8080:{node}:{PORT} login.sherlock.stanford.edu\n"
        f"then open http://localhost:8080 and paste your token into the page.",
        flush=True,
    )
    yield


# dependencies=... applies the token check to every endpoint below; the page
# itself (mounted at the bottom) stays open so you can paste the token into it.
app = FastAPI(title="HPC Web GUI Server", lifespan=lifespan, dependencies=[Depends(require_token)])


@app.get("/health")
def health():
    return {"status": "ok", "node": socket.gethostname(), "port": PORT}


@app.get("/api/results")
def list_results():
    """Files available for download, newest first."""
    files = [p for p in RESULTS_DIR.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "name": p.name,
            "size_bytes": p.stat().st_size,
            "modified": int(p.stat().st_mtime),
        }
        for p in files
    ]


@app.get("/api/results/{filename}")
def download_result(filename: str):
    """Stream one result file to the browser."""
    path = RESULTS_DIR / safe_name(filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No such result: {filename}")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


@app.get("/api/inputs")
def list_inputs():
    """Files uploaded so far — what a job would read as input."""
    files = [p for p in INPUTS_DIR.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "size_bytes": p.stat().st_size} for p in files]


@app.post("/api/inputs")
def upload_input(file: UploadFile):
    """Accept a file from the browser and write it into INPUTS_DIR.

    This is the laptop -> cluster direction: drop a model input, a parameter
    file, or a small dataset in without a separate scp.
    """
    name = safe_name(file.filename)
    dest = INPUTS_DIR / name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"name": name, "size_bytes": dest.stat().st_size}


# Mounted last so the API routes above take precedence. html=True serves
# static/index.html at "/" — same origin as /api/*, which is the point.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def main():
    uvicorn.run(app, host=BIND_HOST, port=PORT)


if __name__ == "__main__":
    main()
