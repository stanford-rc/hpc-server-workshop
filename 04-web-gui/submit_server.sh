#!/bin/bash
#SBATCH --job-name=web-gui
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=logs/server_%j.out

# The server writes "<node>:<port>" here; you read it to build the SSH tunnel.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_gui.txt"

# Where the page reads results from and writes uploads to. Point RESULTS_DIR at
# your real output directory to browse actual job results.
export RESULTS_DIR="$PWD/results"
export INPUTS_DIR="$PWD/inputs"

# Loopback-only. Nothing else on the cluster can reach this port, and the
# default tunnel form (ssh directly to the compute node) still works because
# the forward terminates on the node's own localhost.
#
# Switch to 0.0.0.0 ONLY if you need the login-node tunnel form. That exposes
# an unauthenticated server to every user on the cluster network. See README.md.
export BIND_HOST="127.0.0.1"

# Leave PORT unset so the server picks a free ephemeral port and avoids
# colliding with anyone else on the same node.

module load python/3.12.1
source venv/bin/activate

python server.py
