"""
server.py — FastAPI data server (Tier 1).

Loads a CSV of HPC job records and exposes REST endpoints to query them.
Writes its address to SERVER_ADDR_FILE on startup so batch clients can find it.

Start manually:
  python server.py

Via SLURM:
  sbatch submit_server.sh
"""

import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException

DATA_FILE = Path(__file__).parent / "data" / "jobs.csv"
ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_server.txt"))
PORT = int(os.environ.get("PORT", 8080))

df: pd.DataFrame = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global df
    df = pd.read_csv(DATA_FILE)
    host = socket.getfqdn()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"http://{host}:{PORT}")
    print(f"Loaded {len(df)} job records.")
    print(f"Server address written to {ADDR_FILE}")
    yield


app = FastAPI(title="HPC Job Data Server", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "records": len(df)}


@app.get("/jobs")
def list_jobs(cluster: str = "", status: str = "", limit: int = 20):
    """List jobs with optional filters."""
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
    uvicorn.run("server:app", host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
