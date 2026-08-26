#!/bin/bash
#SBATCH --job-name=mcp-server
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=logs/server_%j.out

# No GPU. This server does file reads and string matching; the model runs
# client-side (Anthropic). See README.md.

# The server writes "<node>:<port>" here; you read it to build the SSH tunnel.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_mcp.txt"

export DOCS_DIR="$PWD/docs"

# Loopback only — the SSH tunnel terminates on this node's localhost.
export BIND_HOST="127.0.0.1"

# If you forward to a local port other than 8080/8081/8000/3000, add it here
# or the DNS-rebinding check rejects the request with "Invalid Host header".
# export ALLOWED_HOSTS="localhost:9999"

module load python/3.12.1
source venv/bin/activate

python mcp_server.py
