#!/bin/bash
#SBATCH --job-name=model-client      # name shown in the queue
#SBATCH --time=0:30:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=1            # CPU cores for it
#SBATCH --mem=2G                     # memory (RAM) for the job
#SBATCH --output=logs/client_%j.out  # save what the job prints here (%j becomes the job ID)

# Where the server wrote its address. Must match submit_server.sh.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

python client.py
