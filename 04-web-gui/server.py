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

Bind address matters — it has to agree with your tunnel form. See README.md:
  BIND_HOST=127.0.0.1 (default) -> ssh -NfL 8080:localhost:<port> <node>
  BIND_HOST=0.0.0.0             -> ssh -NfL 8080:<node>:<port> login.sherlock.stanford.edu

Start manually:
  python server.py

Via SLURM:
  sbatch submit_server.sh
"""

import os
import shutil
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", BASE_DIR / "results"))
INPUTS_DIR = Path(os.environ.get("INPUTS_DIR", BASE_DIR / "inputs"))

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_gui.txt"))
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")


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

    This server has no authentication — anyone who can reach the port can call
    it. Without this, a filename like "../../.ssh/authorized_keys" would let a
    caller read or write outside the intended directory.
    """
    name = os.path.basename(filename or "")
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {filename!r}")
    return name


@asynccontextmanager
async def lifespan(app: FastAPI):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # "<node>:<port>", matching the format the Sherlock Ollama doc uses, so the
    # tunnel command can be built with shell parameter expansion:
    #   ADDR=$(cat "$SERVER_ADDR_FILE")
    #   ssh -NfL 8080:localhost:${ADDR#*:} ${ADDR%:*}
    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")

    # flush=True: SLURM redirects stdout to a file, which block-buffers by
    # default. Without it these lines can sit unflushed for the life of the
    # job and `tail -f logs/server_<jobid>.out` shows nothing.
    print(
        f"Serving on {BIND_HOST}:{PORT} (node {node})\n"
        f"Address written to {ADDR_FILE}\n"
        f"From your laptop:\n"
        f"  ssh -NfL 8080:localhost:{PORT} {node}\n"
        f"  then open http://localhost:8080",
        flush=True,
    )
    yield


app = FastAPI(title="HPC Web GUI Server", lifespan=lifespan)


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
