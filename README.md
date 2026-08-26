# HPC Server Workshop

How to run persistent servers on Sherlock, and reach them from your own laptop.

You have a dataset, a model, or a pipeline on the cluster, and you want to
query it interactively — from a script, a notebook, or a web page you wrote.
This shows how, five ways, in increasing order of what the user sees.

## Before you start

You need:

- **A Sherlock account**, and `ssh login.sherlock.stanford.edu` working from
  your laptop, Duo included. Tiers 4 and 5 depend on this — the SSH tunnel is
  created *from* your machine, so an Open OnDemand shell can't stand in for it.
- **About 20 GB of `$SCRATCH`** if you use the transformers path in tier 2.
  The other tiers need almost nothing.
- **No GPU for tiers 1, 3, 4, or 5.** Only tier 2 needs one, and it can use an
  instant MIG slice (`sh_dev -g 1`) rather than queueing for a full card.

```bash
git clone git@github.com:bcritt1/hpc-server-workshop.git
cd hpc-server-workshop
```

Most research workflows fall into one of these patterns, taught here in order:

| Tier | What it does | Requires |
|------|-------------|----------|
| [01-data-server](01-data-server/) | Serve a dataset via REST API | Any compute node |
| [02-model-server](02-model-server/) | Serve a model — Ollama or HuggingFace | GPU node or MIG slice |
| [03-mcp-server](03-mcp-server/) | Give Claude structured tool access | Any compute node |
| [04-web-gui](04-web-gui/) | Drive a job from a browser on your laptop | Any compute node |
| [05-ood-access](05-ood-access/) | Same, but in-browser with no tunnel | Open OnDemand |

Each tier is self-contained. Start with tier 1 — the SLURM patterns (server
discovery, sbatch client jobs, OOD notebooks) are the same in all of them.

Slides: [HPC-Server-Workshop.pptx](HPC-Server-Workshop.pptx) — 11 slides
covering all five tiers, plus two short asides: keeping the model on Sherlock,
and when to reach for HuggingFace instead of Ollama.

Tiers 1–3 are driven from a **terminal or a script**. Tiers 4–5 are the
**graphical** path: tier 4 forwards a port so a page you wrote loads in your
laptop's browser; tier 5 uses Open OnDemand, where the browser is already on
the cluster and no forwarding is needed.

---

## The core pattern

Servers on HPC can't bind to a fixed hostname — they land on whatever node SLURM
assigns. The solution used throughout:

1. **Server job** starts and writes `http://<node>:<port>` to a shared file in `$SCRATCH`.
2. **Client** (another job, an sbatch script, or a Jupyter notebook) reads that file to find the server.

```
submit_server.sh  ─→  [compute node: server.py]  ─→  writes $SCRATCH/server_addr.txt
submit_client.sh  ─→  [compute node: client.py]  ─→  reads $SCRATCH/server_addr.txt  ─→  HTTP requests
```

---

## Quick start (Tier 1)

```bash
cd 01-data-server

# One-time setup
module load python/3.12.1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the server (runs on a compute node, writes its address to $SCRATCH)
sbatch submit_server.sh
squeue -u $USER          # note the job id

# Run the client job (reads the address, queries the server)
sbatch submit_client.sh

# Or: run the client interactively once the server job is up
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_server.txt"
python client.py
```

Module versions come and go. If `module load python/3.12.1` fails, run
`ml spider python` for what's currently available — the version appears in every
tier's setup block and sbatch script.

`python/3.14.2` also works: every tier's dependencies resolve identically on
both, torch and transformers included. 3.12.1 is just the conservative default.

---

## Using with Open OnDemand (OOD)

OOD Jupyter sessions run on compute nodes and can reach any other node on the
cluster network. To query your server from a notebook:

```python
from pathlib import Path
import requests

# Read the address the server wrote on startup
base_url = Path("/scratch/users/<SUNET>/hpc_workshop_server.txt").read_text().strip()

# Query the server
stats = requests.get(f"{base_url}/stats").json()
print(stats)
```

Replace `/scratch/users/<SUNET>/` with your actual `$SCRATCH` path (`echo $SCRATCH`
in a terminal to find it).

See [05-ood-access](05-ood-access/) for the other OOD routes — the Interactive
Desktop, the built-in file browser, and packaging your own tool as a custom OOD
app so your lab can launch it.

---

## Reaching a server from your laptop

A server on a compute node is not reachable from your laptop by default. The
browser-facing tiers cover the two ways across:

- **SSH port forwarding** ([04-web-gui](04-web-gui/)) — forward a local port to
  the compute node, then use `http://localhost:8080`. Works with anything
  running on your own machine.
- **Open OnDemand** ([05-ood-access](05-ood-access/)) — the browser is already
  on a compute node, so nothing needs forwarding.

The most common mistake is `ssh -L 8080:localhost:8080 login.sherlock…`, which
forwards to the *login* node's localhost and fails with `connection refused`.
Tier 4 explains the two forms that do work and how the bind address has to
match.

---

## Tier progression

**Tier 1 → 2**: replace the CSV + pandas stack with a language model. The
SLURM pattern is identical; you add a GPU request. Two paths are provided:
**Ollama** (`ml ollama`, nothing to write, runs on an instant MIG slice) and
**transformers** (you write the server, but you get the HuggingFace Hub's
pre-tuned domain- and task-specific models). Ollama is the quicker start.

**Tier 2 → 3**: wrap your server's capabilities as MCP tools. Instead of a
Python client calling specific endpoints, Claude discovers and calls them based
on a natural-language question. Note this tier needs *no* GPU — the tools run
on the cluster, the model runs client-side. Tier 3 also covers the fully-local
variant, where Ollama on a GPU node supplies the model instead.

**Any tier → 4**: put a web page in front of it. Tier 4 serves the page from
the same FastAPI app as the API (so there is no CORS to configure) and covers
the SSH port forwarding needed to reach it from your laptop. It runs the whole
loop: upload an input in the browser, run a job that calls either tier 2
backend (`MODEL_API=openai` for Ollama, `generate` for transformers), download
the output.

**Tier 4 → 5**: skip the tunnel. An Open OnDemand session already runs on a
compute node, so a browser inside it reaches your server directly. Tier 5 also
covers packaging your page as a custom OOD app so your lab can launch it.
