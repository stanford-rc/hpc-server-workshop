# Tier 2 — Model Server

Serve a language model on a GPU node so other jobs, notebooks, or a web page
can call it. Builds on the Tier 1 pattern: the server writes its address to a
file, clients read that file to find it.

There are two ways to do this, and both are here.

## Which path?

| | **A. Ollama** | **B. Transformers** |
|---|---|---|
| Setup | `ml ollama` | `pip install` torch + transformers |
| You write | nothing — Ollama *is* the server | the server (`server.py`) |
| Weights | Ollama's library, many cached on Sherlock | anything on the HuggingFace Hub |
| GPU | works on an instant MIG slice | request a full GPU |
| API | OpenAI-compatible `/v1` | your own `/generate` |

**Path A is the fast one** — no torch install, no model download if the tag is
cached, and no queue wait. Start here.

**Path B is what you want for a specific model.** The real reason to use
transformers is the Hub's pre-tuned, domain- and task-specific models: a
model already fine-tuned for your field or your task, which Ollama's library
doesn't carry. Also gated models, quantization you control, and reproducible
batch inference.

---

## Path A — Ollama

```bash
# Instant MIG slice from the dev partition — no queue wait
sh_dev -g 1 -m 16GB -t 2:00:00
ml ollama
bash submit_ollama.sh          # starts ollama, pulls the model, writes the address
```

In a second shell on the same node:

```bash
python ollama_client.py
```

`submit_ollama.sh` also works as a batch job (`sbatch submit_ollama.sh`) when
you need the server to outlive your terminal.

Pick the model with `MODEL=...`. Sherlock caches many popular tags on-prem, so
a cached pull is fast — but there's no documented way to *query* that cache, so
the only confirmation is `ollama pull` printing `found in on-prem cache`
instead of downloading. **Test your tag before you rely on it.**

The address lands in both `$SCRATCH/hpc_workshop_ollama.txt` (the workshop's
discovery convention) and `~/.ollama_server` (what the Sherlock docs and CLI
coding agents expect).

> Ollama binds loopback here, unlike the Sherlock docs' `0.0.0.0`. An Ollama
> server on `0.0.0.0` lets any user on the cluster network consume your GPU
> allocation and call `/api/pull` and `/api/delete`. Widen it only when you
> need cross-node access: `OLLAMA_BIND=0.0.0.0 sbatch submit_ollama.sh`.

---

## Path B — Transformers

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app — loads HF model, exposes `/generate` and `/health` |
| `client.py` | Python client — sends prompts, prints completions |
| `submit_server.sh` | sbatch script (GPU node, 4h walltime) |
| `submit_client.sh` | sbatch script for the client job |
| `submit_ollama.sh` | Path A: starts Ollama and writes its endpoint |
| `ollama_client.py` | Path A: queries Ollama's `/v1` endpoint |

## Setup

```bash
module load python/3.12.1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Sherlock, use the `pytorch` module instead of installing torch from PyPI:
```bash
module load pytorch/2.3  # check available versions: module spider pytorch
pip install fastapi uvicorn transformers accelerate requests
```

## Run on Sherlock

```bash
# Start the GPU server job
sbatch submit_server.sh

# Watch model load (takes 30–120 seconds)
tail -f logs/server_<jobid>.out

# Run the client once the server is ready
sbatch submit_client.sh

# Or interactively
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"
python client.py
```

## Run locally (CPU, small model only)

```bash
python server.py &    # loads distilgpt2, writes /tmp/hpc_workshop_model.txt
python client.py
```

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Status and model name |
| `POST /generate` | Generate text; body: `{"prompt": "...", "max_new_tokens": 100}` |

## Choosing a model

The default (`distilgpt2`) is tiny and runs on CPU — good for testing the pattern.
For real research, swap `MODEL_NAME` in `submit_server.sh`:

| Model | GPU mem | Use case |
|-------|---------|----------|
| `distilgpt2` | CPU only | Workshop demo |
| `meta-llama/Llama-3.2-1B` | ~4 GB | Small fast model |
| `meta-llama/Llama-3.1-8B` | ~16 GB | Good general model |
| `Qwen/Qwen2.5-32B-AWQ` | ~22 GB | Large model (2× L4 or 1× A100) |

Request more GPU memory with `#SBATCH --mem=32G` and multiple GPUs with
`#SBATCH --gpus=2`.

### Domain- and task-specific models

This is the real argument for Path B. The Hub carries models already tuned for
a field or a task — scientific text (`allenai/scibert_scivocab_uncased`),
biomedical literature (`dmis-lab/biobert-base-cased-v1.2`), protein sequences
(`facebook/esm2_t33_650M_UR50D`) — none of which are in Ollama's library. A
model that already knows your domain's vocabulary usually beats a larger
general one, on a fraction of the GPU.

**One thing to change beyond the model name.** Many of these are encoders, not
text generators, so `pipeline("text-generation", ...)` in `server.py` is the
wrong task for them. Swap it for the task you actually want —
`fill-mask`, `feature-extraction` (embeddings), `text-classification`,
`token-classification` (NER) — and adjust the endpoint's return shape to match.
The SLURM and discovery patterns don't change at all.

## HuggingFace cache

Model weights download from HuggingFace Hub on first use. Set `HF_HOME` to a
persistent location so you don't re-download on every job:

```bash
export HF_HOME="$OAK/models/hf_cache"   # persists long-term
# or
export HF_HOME="$SCRATCH/hf_cache"      # faster I/O, but files deleted after 90 days
```

The `submit_server.sh` sets `HF_HOME=$SCRATCH/hf_cache` by default.

## OOD notebook access

```python
from pathlib import Path
import requests

base_url = Path("/scratch/users/<SUNET>/hpc_workshop_model.txt").read_text().strip()

r = requests.post(f"{base_url}/generate", json={
    "prompt": "The Sherlock cluster is",
    "max_new_tokens": 80,
})
print(r.json()["generated_text"])
```
