"""
server.py — FastAPI data server (Tier 1).

Loads a table of (made-up) cluster job records and answers questions about it
over HTTP. On startup it picks a free port and writes "<machine>:<port>" to
SERVER_ADDR_FILE, so a client can find it.

Any machine on Sherlock can connect, so every request must include the token
from TOKEN_FILE (a long random password). Who can use the server is decided by
who can read that file: chmod 600 for just you, or a group-readable file in
$GROUP_HOME for your lab.

Start it:
  bash submit_server.sh      # inside an sh_dev session
  sbatch submit_server.sh    # or as a batch job
"""

import os
import secrets
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

DATA_FILE = Path(__file__).parent / "data" / "jobs.csv"
ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_server.txt"))
# 0.0.0.0 = accept connections from any machine on Sherlock. The token below
# is what keeps everyone else out.
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))


def pick_port() -> int:
    """Return $PORT if set, else a port nobody on this machine is using."""
    override = os.environ.get("PORT")
    if override:
        return int(override)
    with socket.socket() as probe:
        probe.bind(("", 0))  # port 0 = let the system pick a free one
        return probe.getsockname()[1]


PORT = pick_port()

df: pd.DataFrame = None

if not TOKEN_FILE.exists():
    raise SystemExit(
        f"No token file at {TOKEN_FILE}. Make one first (see the README):\n"
        f"  mkdir -p {TOKEN_FILE.parent}\n"
        f"  python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > {TOKEN_FILE}\n"
        f"  chmod 600 {TOKEN_FILE}"
    )
TOKEN = TOKEN_FILE.read_text().strip()

# Every request must carry the token in an "x-token" header.
token_header = APIKeyHeader(name="x-token", auto_error=False)


def require_token(given: str | None = Security(token_header)):
    # compare_digest takes the same time however much of the token matches,
    # so it can't be guessed one character at a time.
    if not given or not secrets.compare_digest(given, TOKEN):
        raise HTTPException(status_code=401, detail="Missing or wrong token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global df
    df = pd.read_csv(DATA_FILE)
    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")
    # flush=True so the lines show up right away in a batch job's log file.
    print(f"Loaded {len(df)} job records.", flush=True)
    print(f"Listening on {BIND_HOST}:{PORT} on {node}", flush=True)
    print(f"Address written to {ADDR_FILE}", flush=True)
    yield


# dependencies=... applies the token check to every endpoint below. FastAPI's
# own /docs page stays open; use its "Authorize" button to paste the token.
# tryItOutEnabled: the /docs page's input boxes are ready to fill in, without
# first clicking "Try it out".
app = FastAPI(
    title="HPC Job Data Server",
    lifespan=lifespan,
    dependencies=[Depends(require_token)],
    swagger_ui_parameters={"tryItOutEnabled": True},
)


@app.get("/health")
def health():
    return {"status": "ok", "records": len(df)}


@app.get("/jobs")
def list_jobs(
    # Listing the allowed values makes them drop-down menus on the /docs page.
    cluster: Literal["sherlock", "farmshare"] | None = None,
    status: Literal["completed", "failed", "pending", "running"] | None = None,
    limit: int = 20,
):
    """List jobs, optionally only one cluster's or one status's."""
    result = df.copy()
    if cluster:
        result = result[result["cluster"] == cluster]
    if status:
        result = result[result["status"] == status]
    return result.head(limit).to_dict(orient="records")


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    """Fetch a single job by ID."""
    row = df[df["job_id"] == job_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return row.iloc[0].to_dict()


@app.get("/stats")
def get_stats():
    """Summary statistics across all jobs."""
    return {
        "total_jobs": len(df),
        "by_cluster": df["cluster"].value_counts().to_dict(),
        "by_status": df["status"].value_counts().to_dict(),
        "avg_runtime_hours": round(df["runtime_hours"].mean(), 2),
        "avg_cpus": round(df["cpus"].mean(), 2),
        "avg_mem_gb": round(df["mem_gb"].mean(), 2),
    }


def main():
    uvicorn.run(app, host=BIND_HOST, port=PORT)


if __name__ == "__main__":
    main()
