"""
client.py — Batch client for the Tier 1 data server.

Reads the server address from SERVER_ADDR_FILE, waits for the server to be
ready, then queries it. Designed to run inside an sbatch job or interactively.

Usage:
  python client.py
  SERVER_ADDR_FILE=/path/to/addr.txt python client.py

In a Jupyter (OOD) notebook, import and call main() directly, or copy
individual requests calls into cells.
"""

import os
import sys
import time
from pathlib import Path

import requests

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_server.txt"))
MAX_WAIT = 120  # seconds to poll for the server


def wait_for_server(base_url: str, timeout: int = MAX_WAIT) -> bool:
    print(f"Waiting for server at {base_url} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                print("Server is ready.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(5)
    return False


def main():
    if not ADDR_FILE.exists():
        print(f"Address file not found: {ADDR_FILE}")
        print("Start the server first:  sbatch submit_server.sh")
        print("Then check:              squeue -u $USER")
        sys.exit(1)

    base_url = ADDR_FILE.read_text().strip()

    if not wait_for_server(base_url):
        print("Server did not respond within timeout.")
        sys.exit(1)

    # Overall stats
    stats = requests.get(f"{base_url}/stats").json()
    print("\n=== Cluster-wide stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Recent completed Sherlock jobs
    jobs = requests.get(
        f"{base_url}/jobs",
        params={"cluster": "sherlock", "status": "completed", "limit": 5},
    ).json()
    print(f"\n=== Last 5 completed Sherlock jobs ===")
    for job in jobs:
        print(
            f"  [{job['job_id']}] {job['user']:8s}  "
            f"{job['cpus']:3d} CPUs  {job['mem_gb']:4.0f} GB  "
            f"{job['runtime_hours']:.1f}h"
        )

    # Single job lookup
    job = requests.get(f"{base_url}/jobs/1004").json()
    print(f"\n=== Job 1004 ===")
    for k, v in job.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
