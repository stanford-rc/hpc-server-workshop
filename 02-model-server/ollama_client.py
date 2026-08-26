"""
ollama_client.py — client for the Ollama path (Tier 2).

Reads the endpoint Ollama's job wrote, waits until the model can actually
answer, then sends prompts through the OpenAI-compatible /v1 endpoint.

The counterpart to client.py: same job, different backend. client.py talks to
the transformers server's own /generate; this talks to Ollama's /v1, which is
the same API OpenAI clients and CLI coding agents speak. The Sherlock docs use
  OLLAMA_BASE_URL=http://$OLLAMA_HOST/v1
for exactly this reason.

Usage:
  python ollama_client.py
  MODEL=mistral:7b python ollama_client.py
  SERVER_ADDR_FILE=~/.ollama_server python ollama_client.py
"""

import os
import sys
import time
from pathlib import Path

import requests

ADDR_FILE = Path(
    os.path.expanduser(
        os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_ollama.txt")
    )
)
MODEL = os.environ.get("MODEL", "llama3.2:1b")
MAX_WAIT = int(os.environ.get("MAX_WAIT", 300))


def base_url() -> str:
    """Read the endpoint. Accepts "<host>:<port>" or a full URL."""
    if not ADDR_FILE.exists():
        sys.exit(
            f"Address file not found: {ADDR_FILE}\n"
            "Start Ollama first:\n"
            "  sh_dev -g 1 -m 16GB && ml ollama && bash submit_ollama.sh\n"
            "or:\n"
            "  sbatch submit_ollama.sh"
        )
    addr = ADDR_FILE.read_text().strip()
    return addr if addr.startswith("http") else f"http://{addr}"


def wait_for_model(url: str, model: str, timeout: int = MAX_WAIT) -> bool:
    """Poll until the *model* is listed, not merely until the port answers.

    A pull can still be syncing after the daemon starts accepting connections.
    Waiting on the port alone gets you a 404 for a model that isn't loaded yet.
    """
    print(f"Waiting for {model} at {url} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/api/tags", timeout=5)
            if r.status_code == 200:
                names = [m.get("name", "") for m in r.json().get("models", [])]
                if any(n == model or n.startswith(f"{model}:") for n in names):
                    print(f"Ready. Models present: {', '.join(names)}")
                    return True
                print(f"  daemon up, {model} not loaded yet (have: {names or 'none'})")
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    return False


def chat(url: str, model: str, prompt: str, max_tokens: int = 120) -> str:
    """One turn through the OpenAI-compatible endpoint."""
    r = requests.post(
        f"{url}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def main():
    url = base_url()
    if not wait_for_model(url, MODEL):
        sys.exit(f"{MODEL} did not become available within {MAX_WAIT}s.")

    prompts = [
        "In one sentence, what is a SLURM partition?",
        "Name three good reasons to write job output to scratch storage.",
    ]
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        print(f"Answer: {chat(url, MODEL, prompt)}")


if __name__ == "__main__":
    main()
