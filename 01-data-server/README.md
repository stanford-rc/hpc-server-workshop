# Tier 1 — Data Server

A FastAPI server that loads a CSV of HPC job records and exposes REST endpoints.
Demonstrates the core SLURM server pattern: discovery via shared file, sbatch
server job, sbatch client job, and OOD notebook access.

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app — loads `data/jobs.csv`, exposes `/jobs`, `/stats`, `/health` |
| `client.py` | Python client — reads server address, queries endpoints |
| `submit_server.sh` | sbatch script to start the server on a compute node |
| `submit_client.sh` | sbatch script to run the client as a dependent job |
| `data/jobs.csv` | Sample job records (synthetic) |

## Setup

```bash
module load python/3.12.1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run on Sherlock

```bash
# Start the server (runs until the job walltime expires)
sbatch submit_server.sh

# Watch it start up
tail -f logs/server_<jobid>.out

# Once running, submit the client job
sbatch submit_client.sh

# Or run the client interactively
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_server.txt"
python client.py
```

## Run locally (no SLURM)

```bash
python server.py &              # starts on port 8080, writes /tmp/hpc_workshop_server.txt
python client.py                # connects and queries
```

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Server status and record count |
| `GET /jobs` | List jobs; optional `?cluster=sherlock&status=completed&limit=20` |
| `GET /jobs/{job_id}` | Single job by ID |
| `GET /stats` | Aggregate statistics across all jobs |

## Key concepts

**Server discovery**: `server.py` writes `http://<hostname>:<port>` to
`$SERVER_ADDR_FILE` on startup. `client.py` reads that file to find the server.
Both scripts read `SERVER_ADDR_FILE` from the environment — the sbatch scripts
set it to `$SCRATCH/hpc_workshop_server.txt` so both jobs use the same path.

**Walltime planning**: servers need enough walltime to be useful. A 4-hour job
is a reasonable starting point. Client jobs can be shorter.

**OOD access**: see the top-level README for the notebook snippet, and
[05-ood-access](../05-ood-access/) for the other in-browser routes.

**Free GUI**: FastAPI serves interactive API docs at `/docs` (Swagger UI) and
`/redoc` with no extra code. Forward the port as described in
[04-web-gui](../04-web-gui/README.md#2-you-forward-a-local-port-to-it), then
open `http://localhost:8080/docs` to click through `/jobs` and `/stats` from
your laptop. To build your own page instead of using Swagger's, see tier 4.

## Adapting to your data

Swap `data/jobs.csv` for your own dataset and update the endpoints in `server.py`.
The SLURM scripts and discovery pattern stay the same.
