#!/bin/bash
#SBATCH --job-name=web-gui           # name shown in the queue
#SBATCH --time=1:00:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=2            # CPU cores for it
#SBATCH --mem=4G                     # memory (RAM) for the job
#SBATCH --output=logs/server_%j.out  # save what the job prints here (%j becomes the job ID)

# The server writes "<machine>:<port>" here; you need it for the SSH tunnel.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_gui.txt"

# Where the page lists results from, and where uploads go. Point RESULTS_DIR
# at your own output folder to browse real job results.
export RESULTS_DIR="$PWD/results"
export INPUTS_DIR="$PWD/inputs"

# Any machine on Sherlock can connect; requests need your token (see Tier 1).
export BIND_HOST="0.0.0.0"

# PORT is left unset, so the server picks a free port and writes it down.

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

python server.py
