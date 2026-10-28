#!/bin/bash
#SBATCH --job-name=ollama-server     # name shown in the queue
#SBATCH --time=1:00:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --nodes=1                    # keep everything on one machine
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=4            # CPU cores for it
#SBATCH --gpus=1                     # number of GPUs
#SBATCH --partition=gpu              # the machines that have GPUs
#SBATCH --output=logs/ollama_%j.out  # save what the job prints here (%j becomes the job ID)

# Starts Ollama, a ready-made program that serves language models, so you
# don't write a server yourself. Other programs send it questions over the
# network in the same format OpenAI's service uses (at /v1).
#
# In the workshop you run this script by hand inside an interactive session on
# a GPU slice (a share of one GPU), which usually starts right away:
#
#   sh_dev -g 1 -t 1:00:00
#   ml ollama
#   bash submit_ollama.sh
#
# Submitting it with sbatch instead also works, and keeps the server running
# after you close your terminal.
#
# Sherlock's Ollama docs: https://www.sherlock.stanford.edu/docs/software/using/ollama/

set -uo pipefail

# Which model to serve. Override with MODEL=... ; keep it small enough for a
# GPU slice. Sherlock keeps copies of many popular models. When the model is
# one of them, the download step below prints "found in on-prem cache".
MODEL="${MODEL:-llama3.2:1b}"

# Only accept connections from this same machine (127.0.0.1). Ollama has no
# password, so opening it to the whole cluster (0.0.0.0) would let anyone on
# Sherlock use your GPU and add or delete models. Open it up only if a program
# on another machine needs to reach it:
#
#   OLLAMA_BIND=0.0.0.0 sbatch submit_ollama.sh
OLLAMA_BIND="${OLLAMA_BIND:-127.0.0.1}"

ADDR_FILE="${SERVER_ADDR_FILE:-$SCRATCH/hpc_workshop_ollama.txt}"

# Load Ollama unless you already did (ml ollama, in the interactive route).
command -v ollama >/dev/null 2>&1 || ml ollama

# Pick a random port (the numbered "door" the server listens on) that nobody
# else on this machine is using. Same approach as Sherlock's Ollama docs.
OLLAMA_PORT=$(( RANDOM % 60000 + 1024 ))
while (echo > /dev/tcp/localhost/$OLLAMA_PORT) &>/dev/null; do
    OLLAMA_PORT=$(( ( RANDOM % 60000 ) + 1024 ))
done

# The name of the machine this is running on.
NODE=$(hostname)

echo "Starting ollama on $NODE:$OLLAMA_PORT (bind $OLLAMA_BIND), model $MODEL"

export OLLAMA_HOST="$OLLAMA_BIND:$OLLAMA_PORT"
ollama serve &
SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null' EXIT

# Give Ollama up to 30 seconds to start before asking it for the model.
for _ in $(seq 1 30); do
    curl -sf "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1 && break
    sleep 1
done

echo "Pulling $MODEL (watch for 'found in on-prem cache')..."
ollama pull "$MODEL"

# Write the address down only now that the model is ready, so a client that
# finds the address can use it right away.
mkdir -p "$(dirname "$ADDR_FILE")"
echo "$NODE:$OLLAMA_PORT" > "$ADDR_FILE"
# Also write it where Sherlock's docs and AI coding tools look for it.
echo "$NODE:$OLLAMA_PORT" > "$HOME/.ollama_server"

cat <<EOF

Ollama ready.
  model:     $MODEL
  endpoint:  http://$NODE:$OLLAMA_PORT
  addr file: $ADDR_FILE  (and ~/.ollama_server)

To use it, open a second terminal, ssh to $NODE from a login node, then:
  python ollama_client.py

EOF

# Keep the job running for as long as Ollama runs.
wait $SERVE_PID
