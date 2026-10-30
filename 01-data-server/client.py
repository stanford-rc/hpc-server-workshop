"""
client.py — Batch client for the Tier 1 data server.

Brad Rittenhouse, Stanford Research Computing (bcritt@stanford.edu)

Reads the server's address from SERVER_ADDR_FILE and the token from TOKEN_FILE,
waits for the server to be ready, then asks it a few questions. Works from any
machine on Sherlock.

Usage:
  bash submit_client.sh
  SERVER_ADDR_FILE=/path/to/addr.txt python client.py
"""

import os
import sys
import time
from pathlib import Path

import requests

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_server.txt"))
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))
MAX_WAIT = 120  # seconds to keep checking whether the server is up


def wait_for_server(base_url: str, headers: dict, timeout: int = MAX_WAIT) -> bool:
    print(f"Waiting for server at {base_url} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/health", headers=headers, timeout=5)
            if r.status_code == 401:
                sys.exit(f"The server refused the token in {TOKEN_FILE}.")
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
        print("Start the server first:  bash submit_server.sh")
        sys.exit(1)

    if not TOKEN_FILE.exists():
        sys.exit(f"No token file at {TOKEN_FILE}. It's made during setup (see the README).")

    base_url = f"http://{ADDR_FILE.read_text().strip()}"
    headers = {"x-token": TOKEN_FILE.read_text().strip()}  # sent with every request

    if not wait_for_server(base_url, headers):
        print("Server did not respond. If it has stopped, the address file is left over:")
        print(f"start the server again, or delete {ADDR_FILE}.")
        sys.exit(1)

    # Overall stats
    stats = requests.get(f"{base_url}/stats", headers=headers).json()
    print("\n=== Cluster-wide stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Completed Sherlock jobs (the first 5 in the table)
    jobs = requests.get(
        f"{base_url}/jobs",
        params={"cluster": "sherlock", "status": "completed", "limit": 5},
        headers=headers,
    ).json()
    print(f"\n=== First 5 completed Sherlock jobs ===")
    for job in jobs:
        print(
            f"  [{job['job_id']}] {job['user']:8s}  "
            f"{job['cpus']:3d} CPUs  {job['mem_gb']:4.0f} GB  "
            f"{job['runtime_hours']:.1f}h"
        )

    # Single job lookup
    job = requests.get(f"{base_url}/jobs/1004", headers=headers).json()
    print(f"\n=== Job 1004 ===")
    for k, v in job.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
