# CLAUDE.md

## Project

Teaching material for running persistent servers on Sherlock (Stanford's SLURM
cluster) and reaching them from a laptop. Five self-contained tiers plus a
slide deck. The audience is researchers, not sysadmins.

## Conventions

- **Everything is Sherlock-specific**: `$SCRATCH`, `module load`, `sbatch`,
  `sh_dev`, MIG slices, `ondemand.sherlock.stanford.edu`. Don't generalize the
  examples to other schedulers — the point is that they work as written.
- **Two things every tier shares**: the server writes `<node>:<port>` to a
  discovery file, and clients read that file. Don't hardcode hostnames or ports.
- **Servers bind `0.0.0.0` and require a token.** Every request must carry the
  contents of `~/.hpc_workshop/token` (`$TOKEN_FILE`) in an `x-token` header;
  Tier 4 also accepts it as an `x-token` cookie so plain download links work.
  File permissions on the token file decide who can use a server (600 = just
  you, group-readable in `$GROUP_HOME` = the lab). Ollama can't check a token,
  so it stays on `127.0.0.1` and its clients run on its own machine.
- **The workshop runs in `sh_dev` sessions.** `dev` rejects `sbatch`, and GPU
  slices (A30 MIG, 6 GB) exist only there. Learners run scripts with
  `bash submit_*.sh`; the `#SBATCH` lines are for running for real on
  `normal`/`gpu`. Each user gets at most 2 dev sessions, 4 cores, 16 GB.
- **Python comes from `ml python/3.12.1` plus the shared environment** at
  `/home/groups/sh_support/bcritt/server_workshop/venv` (built by
  `build-env.sh` there, with `uv pip install --no-build`). The Tier 2 model is
  pre-downloaded to `server_workshop/hf_cache`.
- **Test every learner-facing command on `dev`, exactly as written.**
- **Cite Sherlock's public docs** (`sherlock.stanford.edu/docs`) rather than
  internal wikis or support tickets. This repo goes to researchers.
- Pinned module versions drift. If `python/3.12.1` is stale, the fix is in
  every tier's setup block *and* every sbatch script.

## Slides

`HPC-Server-Workshop.pptx` is **generated** from the SRC branded template by
`slides-src/build.sh` + `fill.py`. Hand-editing the `.pptx` gets silently
discarded on the next rebuild — edit `fill.py` instead. See `slides-src/README.md`.

## Working agreement

- Never run `git commit` or `git push` without explicit instruction.
- Untested-on-hardware code should say so. Much of this was written and tested
  off-cluster; anything that hasn't run on Sherlock itself is marked in the
  relevant README.
