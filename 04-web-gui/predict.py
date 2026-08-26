"""
predict.py — the compute step that produces the output the site serves.

This is the middle of the workflow:

  browser upload  ->  INPUTS_DIR  ->  [predict.py]  ->  RESULTS_DIR  ->  browser download
                                            |
                                            +-- POST /generate on the Tier 2 model server

It reads a prompt file from INPUTS_DIR (one prompt per line), sends each prompt
to a Tier 2 model server, and writes the completions to RESULTS_DIR as both
JSONL and CSV. Nothing here is GUI-aware — it just reads and writes the two
directories the server exposes, which is the point: your existing batch script
becomes a web app without being rewritten.

Either Tier 2 backend works. Pick with MODEL_API:
  openai    Ollama's OpenAI-compatible /v1/chat/completions  (workshop path)
  generate  the transformers server's own /generate          (default)

Usage:
  python predict.py                    # newest .txt in INPUTS_DIR
  python predict.py prompts.txt        # a specific file in INPUTS_DIR

Requires a Tier 2 server to be running:
  cd ../02-model-server && sbatch submit_ollama.sh    # MODEL_API=openai
  cd ../02-model-server && sbatch submit_server.sh    # MODEL_API=generate
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", BASE_DIR / "results"))
INPUTS_DIR = Path(os.environ.get("INPUTS_DIR", BASE_DIR / "inputs"))

# Written by 02-model-server/server.py or submit_ollama.sh on startup.
MODEL_ADDR_FILE = Path(
    os.path.expanduser(
        os.environ.get("MODEL_ADDR_FILE", "/tmp/hpc_workshop_model.txt")
    )
)
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", 60))

# Which Tier 2 backend to talk to. Explicit rather than probed: auto-detection
# would add a failure mode that's awkward to debug from a job log.
MODEL_API = os.environ.get("MODEL_API", "generate")
# Only used by MODEL_API=openai — Ollama requires a model name in the request.
MODEL = os.environ.get("MODEL", "llama3.2:1b")


def model_base_url() -> str:
    """Read the model server's address from its discovery file.

    Tier 2 writes "http://<host>:<port>"; Tier 4 writes "<host>:<port>".
    Accept either so this works no matter which file you point it at.
    """
    if not MODEL_ADDR_FILE.exists():
        sys.exit(
            f"Model server address file not found: {MODEL_ADDR_FILE}\n"
            "Start a Tier 2 server first:\n"
            "  cd ../02-model-server && sbatch submit_ollama.sh   # MODEL_API=openai\n"
            "  cd ../02-model-server && sbatch submit_server.sh   # MODEL_API=generate"
        )
    addr = MODEL_ADDR_FILE.read_text().strip()
    return addr if addr.startswith("http") else f"http://{addr}"


def complete(base_url: str, prompt: str) -> tuple[str, str]:
    """Send one prompt. Returns (completion, model_name).

    The two backends differ in more than the URL: /generate echoes the prompt
    back as part of generated_text, while a chat completion returns only the
    reply. Normalising that here keeps the output files identical either way.
    """
    if MODEL_API == "openai":
        r = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": MAX_NEW_TOKENS,
            },
            timeout=180,
        )
        r.raise_for_status()
        payload = r.json()
        return payload["choices"][0]["message"]["content"].strip(), payload.get("model", MODEL)

    if MODEL_API != "generate":
        sys.exit(f"Unknown MODEL_API={MODEL_API!r}. Use 'openai' or 'generate'.")

    r = requests.post(
        f"{base_url}/generate",
        json={"prompt": prompt, "max_new_tokens": MAX_NEW_TOKENS},
        timeout=180,
    )
    r.raise_for_status()
    payload = r.json()
    # The pipeline echoes the prompt; keep only the continuation.
    return payload["generated_text"][len(prompt):].strip(), payload["model"]


def pick_input(argv: list[str]) -> Path:
    """Use the named input file, or the most recently uploaded .txt."""
    if len(argv) > 1:
        path = INPUTS_DIR / os.path.basename(argv[1])
        if not path.is_file():
            sys.exit(f"No such input file: {path}")
        return path

    candidates = sorted(
        INPUTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        sys.exit(
            f"No .txt input files in {INPUTS_DIR}\n"
            "Upload one through the web page, or drop a file there directly."
        )
    return candidates[0]


def main():
    if MODEL_API not in ("openai", "generate"):
        sys.exit(f"Unknown MODEL_API={MODEL_API!r}. Use 'openai' or 'generate'.")

    base_url = model_base_url()
    input_path = pick_input(sys.argv)

    prompts = [ln.strip() for ln in input_path.read_text().splitlines() if ln.strip()]
    if not prompts:
        sys.exit(f"{input_path.name} has no non-empty lines.")

    print(f"Model server: {base_url}  (MODEL_API={MODEL_API})")
    print(f"Input: {input_path.name} ({len(prompts)} prompts)")

    rows = []
    for i, prompt in enumerate(prompts, start=1):
        completion, model = complete(base_url, prompt)
        rows.append({"prompt": prompt, "completion": completion, "model": model})
        print(f"  [{i}/{len(prompts)}] {prompt[:50]!r} -> {len(completion)} chars")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stem = input_path.stem

    jsonl_path = RESULTS_DIR / f"{stem}_{stamp}.jsonl"
    with jsonl_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    csv_path = RESULTS_DIR / f"{stem}_{stamp}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "completion", "model"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {jsonl_path.name} and {csv_path.name} to {RESULTS_DIR}")
    print("Refresh the web page — both files are now listed for download.")


if __name__ == "__main__":
    main()
