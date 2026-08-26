# Tier 4 — Web GUI

Drive a job from a browser on your own laptop: upload an input, run the job,
download the output. This is the tier that answers "can I build a small site to
interact with my research data?"

The site itself is deliberately boring — one HTML file, no framework, no build
step. The part worth learning is the plumbing that gets a browser on your
laptop talking to a server on a compute node.

## The whole workflow

```
   your laptop                    SSH tunnel            Sherlock compute node
  ┌────────────┐                                       ┌───────────────────┐
  │  browser   │ ── upload input ────────────────────▶ │  inputs/          │
  │ localhost  │                                       │       │           │
  │   :8080    │                                       │       ▼           │
  │            │                                       │  predict.py ──────┼──▶ Tier 2
  │            │                                       │       │           │    model
  │            │ ◀── download output ───────────────── │  results/         │    server
  └────────────┘                                       └───────────────────┘
```

Three steps, three files:

| Step | What runs | Where |
|------|-----------|-------|
| 1. Serve the page + API | `server.py` (`sbatch submit_server.sh`) | long-running job |
| 2. Produce the output | `predict.py` (`sbatch submit_job.sh`) | short job |
| 3. View / transfer | your browser, through the tunnel | your laptop |

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app — serves `static/index.html` *and* the JSON/file API |
| `static/index.html` | The entire GUI. Vanilla JS, no dependencies |
| `predict.py` | Compute step — reads `inputs/`, calls the Tier 2 model server, writes `results/` |
| `submit_server.sh` | sbatch script for the long-running web server |
| `submit_job.sh` | sbatch script for the compute step |
| `results/` | What the page offers for download (ships with a sample run) |
| `inputs/` | Where browser uploads land |
| `requirements.txt` | FastAPI, uvicorn, python-multipart, requests |

## Setup

```bash
module load python/3.12.1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# SLURM needs this to exist before you submit — --output is resolved at
# submit time, and logs/ is gitignored so a fresh clone won't have it.
mkdir -p logs
```

---

## The plumbing, in detail

### 1. The server picks a port and writes down where it landed

Servers on HPC can't bind a fixed hostname — SLURM decides which node you get.
And a hardcoded port collides with whoever else is on that node. So `server.py`
binds an **ephemeral** port and writes `<node>:<port>` to a known file:

```bash
$ cat $SCRATCH/hpc_workshop_gui.txt
sh03-01n52:41235
```

That `<node>:<port>` format is the same one the [Sherlock Ollama
docs][ollama] use for `~/.ollama_server`, and for the same reason: you can pull
both halves back out with shell parameter expansion instead of copying a port
out of a log file by hand.

### 2. You forward a local port to it

This is the step that trips everyone up. Two forms work, and **the tunnel
target must agree with what the server bound to**:

| Server bound to | Tunnel from your laptop | Notes |
|---|---|---|
| `127.0.0.1` (default here) | `ssh -NfL 8080:localhost:PORT NODE` | Encrypted end to end. Needs an active job on `NODE` |
| `0.0.0.0` | `ssh -NfL 8080:NODE:PORT login.sherlock.stanford.edu` | Last hop is cleartext on the internal network |

The default is the first form. Copy-paste version:

```bash
ADDR=$(cat $SCRATCH/hpc_workshop_gui.txt)      # e.g. sh03-01n52:41235
ssh -NfL 8080:localhost:${ADDR#*:} ${ADDR%:*}
```

`${ADDR#*:}` is the port, `${ADDR%:*}` is the node. `-N` means "no remote
command", `-f` backgrounds it. To close the tunnel later:
`pkill -f "8080:localhost"`.

Why this form by default: SSH terminates the forward on the compute node's own
`localhost`, so the server never has to listen on a network-visible address.
It works because Sherlock lets you SSH to a compute node **where you have a
running job** — and here the server job *is* yours. On a node where you don't,
you'll get `Access denied by pam_slurm_adopt: you have no active jobs on this
node`.

Use the login-node form if you can't SSH to the node. One tradeoff to know:
with `-L 8080:NODE:8080 login`, SSH only encrypts as far as the login node; the
login→compute hop crosses the internal network in the clear. Adding a jump host
closes that gap:

```bash
ssh -J login.sherlock.stanford.edu -L 8080:localhost:PORT NODE
```

### 3. You open `http://localhost:8080`

Not the node's hostname — `localhost`. The tunnel makes your laptop's port 8080
*be* the server's port.

> **The classic failure.** `ssh -L 8050:localhost:8050 login.sherlock` then
> `channel 3: open failed: connect failed: Connection refused`. That forwards to
> the **login node's** localhost, where nothing is listening — the server is on
> a compute node. This is the single most common version of this mistake — and
> note the second half of the trap: fixing the tunnel target isn't enough if the
> server is bound to loopback on a node you're forwarding *through*. The bind
> address and the tunnel target have to agree.

### Why the page and the API come from one server

`server.py` serves `static/index.html` at `/` and the API at `/api/*`. So the
browser's origin and every `fetch()` target are both
`http://localhost:8080` — **same origin**, which means no CORS headers, no
preflight, no second web server, no frontend build.

If you instead open `index.html` from your laptop's filesystem and point it at
the tunnel, the origin is `file://` and every request is cross-origin. That's
the point at which people start adding `CORSMiddleware` and wildcard origins to
an unauthenticated server. Serving both from one app avoids the whole problem.

In `static/index.html` this is why every path is relative:

```js
const files = await (await fetch("/api/results")).json();
```

---

## Run it

```bash
# 1. Start the web server (long-running)
sbatch submit_server.sh
tail -f logs/server_<jobid>.out     # prints the exact ssh command to use

# 2. Open the tunnel from your laptop, then browse to localhost:8080
ADDR=$(cat $SCRATCH/hpc_workshop_gui.txt)
ssh -NfL 8080:localhost:${ADDR#*:} ${ADDR%:*}

# 3. Upload a prompts file through the page (one prompt per line)

# 4. Start the Tier 2 model server, then run the compute step
cd ../02-model-server && sbatch submit_server.sh && cd -
sbatch submit_job.sh

# 5. Refresh the page — the new .csv and .jsonl are listed for download
```

Locally, without SLURM:

```bash
python server.py            # prints its port; open that URL directly
python predict.py           # needs the Tier 2 server running
```

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Status, node, and port |
| `GET /api/results` | List downloadable outputs, newest first |
| `GET /api/results/{name}` | Download one output file |
| `GET /api/inputs` | List uploaded inputs |
| `POST /api/inputs` | Upload a file (multipart form field `file`) |
| `GET /` | The page itself |

## Security

These servers have **no authentication** — anyone who can reach the port can
call every endpoint, including the upload. That's tolerable only because the
SSH tunnel is doing the access control for you: reaching the port at all
requires your SUNet ID, 2FA, and an SSH session.

So:

- **Keep `BIND_HOST=127.0.0.1`.** On `0.0.0.0` every user on the cluster
  network can reach an unauthenticated file-upload endpoint.
- **Don't try to expose this publicly.** Research clusters are not web hosting
  platforms; the supported way in is an SSH tunnel. Running a plain-HTTP app on
  a compute node and opening it up is the kind of thing that attracts a
  security finding, so don't. If you need a genuinely shared service, talk to
  SRCC rather than widening a bind address.
- **`safe_name()` in `server.py` is load-bearing.** Without it, an upload named
  `../../../.ssh/authorized_keys` would write outside `inputs/`.

For a genuinely shared, authenticated service you want a persistent host with
nginx, TLS, and real tokens — not an sbatch job on a compute node. That's a
conversation with SRCC, not a change to these scripts.

## Adapting this

Point `RESULTS_DIR` at a directory your real pipeline already writes to and the
page immediately lists those files — `server.py` needs no changes. `predict.py`
is the template for the compute step: it only reads `inputs/` and writes
`results/`, so it knows nothing about the web layer. Your existing batch script
can take its place as-is.

To show a plot or a table of numbers rather than a file list, add an endpoint
that returns parsed JSON and render it in `index.html`.

[ollama]: https://www.sherlock.stanford.edu/docs/software/using/ollama/
