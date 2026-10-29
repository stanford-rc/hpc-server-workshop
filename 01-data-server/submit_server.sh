#!/bin/bash
#SBATCH --job-name=data-server       # name shown in the queue
#SBATCH --time=1:00:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=2            # CPU cores for it
#SBATCH --mem=4G                     # memory (RAM) for the job
#SBATCH --output=logs/server_%j.out  # save what the job prints here (%j becomes the job ID)

# The server can land on any machine in the cluster, so it writes its address
# to this file when it starts. Other jobs read the file to find it. $SCRATCH is
# your scratch folder, which every Sherlock machine can see.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_server.txt"

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

rm -f "$SERVER_ADDR_FILE"   # clear any address left by an earlier server
python server.py
