#!/bin/bash
#SBATCH --job-name=mcp-server        # name shown in the queue
#SBATCH --time=1:00:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=2            # CPU cores for it
#SBATCH --mem=4G                     # memory (RAM) for the job
#SBATCH --output=logs/server_%j.out  # save what the job prints here (%j becomes the job ID)

# No GPU needed: this server only reads files and searches their text. The AI
# model itself runs at Anthropic, behind Claude Code.

# The server writes "<machine>:<port>" here, so Claude Code can find it.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_mcp.txt"

# The folder of documents the server lets Claude search and read.
export DOCS_DIR="$PWD/docs"

# Any machine on Sherlock can connect; requests need your token (see Tier 1).
export BIND_HOST="0.0.0.0"

# Only for connecting from your laptop (see the README): if your tunnel uses a
# laptop port other than 8080, 8081, 8000 or 3000, add it here, or the server
# refuses requests with "Invalid Host header".
# export ALLOWED_HOSTS="localhost:9999"

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

rm -f "$SERVER_ADDR_FILE"   # clear any address left by an earlier server
python mcp_server.py
