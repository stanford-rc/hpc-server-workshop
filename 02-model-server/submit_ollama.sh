#!/bin/bash
#SBATCH --job-name=ollama-server
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gpus=1
#SBATCH --partition=gpu
#SBATCH --output=logs/ollama_%j.out

# Ollama path — the quick way to get a model serving on Sherlock.
#
# Ollama *is* the server, so there is no server.py here. You get an
# OpenAI-compatible endpoint at /v1 plus Ollama's native API at /api.
#
# For the workshop, prefer the interactive route instead of this script — a MIG
# slice from the dev partition is available immediately, with no queue wait:
#
#   sh_dev -g 1 -m 16GB -t 2:00:00
#   ml ollama
#   bash submit_ollama.sh          # runs the body below directly
#
# Submit as a batch job only when you need it to outlive your terminal. Note
# there is deliberately no --constraint here: over-constraining is the most
# common reason a GPU job pends forever, and the default is fine for a small
# model. Add one only if you need a specific card.
#
# Docs: https://www.sherlock.stanford.edu/docs/software/using/ollama/

set -uo pipefail

# Pick the model with MODEL=... . Keep it small for a MIG slice.
#
# There is no documented way to query Sherlock's on-prem model cache, so the
# only confirmation that a tag is cached is `ollama pull` printing
# "found in on-prem cache" instead of downloading from the internet. Test the
# tag you plan to use *before* the workshop.
MODEL="${MODEL:-llama3.2:1b}"

# Loopback by default, matching tiers 3-4. An Ollama server on 0.0.0.0 lets any
# user on the cluster network use your GPU allocation and call /api/pull and
# /api/delete — so only widen this if you need to reach it from another node
# (e.g. running tier 4's predict.py as a separate job):
#
#   OLLAMA_BIND=0.0.0.0 sbatch submit_ollama.sh
OLLAMA_BIND="${OLLAMA_BIND:-127.0.0.1}"

ADDR_FILE="${SERVER_ADDR_FILE:-$SCRATCH/hpc_workshop_ollama.txt}"

# Only load the module if it isn't already (the sh_dev route loads it by hand).
command -v ollama >/dev/null 2>&1 || ml ollama

# Free ephemeral port, same approach as the Sherlock Ollama doc.
OLLAMA_PORT=$(( RANDOM % 60000 + 1024 ))
while (echo > /dev/tcp/localhost/$OLLAMA_PORT) &>/dev/null; do
    OLLAMA_PORT=$(( ( RANDOM % 60000 ) + 1024 ))
done

# $SLURM_NODELIST is a range expression on multi-node allocations
# (sh03-[01-02]n52), which is not a hostname. --nodes=1 above plus `hostname`
# keeps this a single resolvable name.
NODE=$(hostname)

echo "Starting ollama on $NODE:$OLLAMA_PORT (bind $OLLAMA_BIND), model $MODEL"

export OLLAMA_HOST="$OLLAMA_BIND:$OLLAMA_PORT"
ollama serve &
SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null' EXIT

# Wait for the daemon before pulling.
for _ in $(seq 1 30); do
    curl -sf "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1 && break
    sleep 1
done

echo "Pulling $MODEL (watch for 'found in on-prem cache')..."
ollama pull "$MODEL"

# Write the address only once the model can actually answer. A client that
# connects mid-pull gets a 404 for a model that is still syncing, which reads
# as a broken workshop rather than "wait 30 seconds".
mkdir -p "$(dirname "$ADDR_FILE")"
echo "$NODE:$OLLAMA_PORT" > "$ADDR_FILE"
# Also write the path every Sherlock doc and CLI-agent config expects.
echo "$NODE:$OLLAMA_PORT" > "$HOME/.ollama_server"

cat <<EOF

Ollama ready.
  model:     $MODEL
  endpoint:  http://$NODE:$OLLAMA_PORT
  addr file: $ADDR_FILE  (and ~/.ollama_server)

Same allocation:
  python ollama_client.py

From your laptop (tunnel, then point a client at http://localhost:8080/v1):
  ssh -NfL 8080:localhost:$OLLAMA_PORT $NODE

EOF

# Hold the allocation open for as long as the daemon runs.
wait $SERVE_PID
