"""
client.py — Batch client for the Tier 2 model server.

Reads the server address from SERVER_ADDR_FILE, waits for the model to load,
then sends prompts and prints completions.

Model startup can take 30–120 seconds; the client polls until ready.

Usage:
  python client.py
  SERVER_ADDR_FILE=/path/to/addr.txt python client.py

In a Jupyter (OOD) notebook:
  import requests
  base_url = open("/path/to/addr.txt").read().strip()
  r = requests.post(f"{base_url}/generate", json={"prompt": "...", "max_new_tokens": 50})
  print(r.json()["generated_text"])
"""

import os
import sys
import time
from pathlib import Path

import requests

ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_model.txt"))
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))
MAX_WAIT = 300  # model load can take a few minutes


def wait_for_server(base_url: str, headers: dict, timeout: int = MAX_WAIT) -> bool:
    print(f"Waiting for model server at {base_url} ...")
    print("(Model load may take 30–120 seconds.)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/health", headers=headers, timeout=5)
            if r.status_code == 401:
                sys.exit(f"The server refused the token in {TOKEN_FILE}.")
            if r.status_code == 200:
                info = r.json()
                print(f"Server ready. Model: {info['model']}")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(10)
    return False


def generate(base_url: str, headers: dict, prompt: str, max_new_tokens: int = 100) -> str:
    r = requests.post(
        f"{base_url}/generate",
        headers=headers,
        json={"prompt": prompt, "max_new_tokens": max_new_tokens},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["generated_text"]


def main():
    if not ADDR_FILE.exists():
        print(f"Address file not found: {ADDR_FILE}")
        print("Start the server first:  bash submit_server.sh")
        sys.exit(1)
    if not TOKEN_FILE.exists():
        sys.exit(f"No token file at {TOKEN_FILE}. It's made in Tier 1 setup.")

    base_url = f"http://{ADDR_FILE.read_text().strip()}"
    headers = {"x-token": TOKEN_FILE.read_text().strip()}  # sent with every request

    if not wait_for_server(base_url, headers):
        print("Server did not respond. If it has stopped, the address file is left over:")
        print(f"start the server again, or delete {ADDR_FILE}.")
        sys.exit(1)

    prompts = [
        "The Sherlock HPC cluster at Stanford is",
        "To run a GPU job on Sherlock, the SLURM command is",
        "The best way to store large datasets on an HPC system is",
    ]

    for prompt in prompts:
        print(f"\nPrompt: {prompt!r}")
        result = generate(base_url, headers, prompt, max_new_tokens=60)
        continuation = result[len(prompt):]
        print(f"Output: {continuation.strip()}")


if __name__ == "__main__":
    main()
