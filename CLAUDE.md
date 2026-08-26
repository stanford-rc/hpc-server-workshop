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
- **Servers bind `127.0.0.1` by default.** None of them authenticate anyone;
  the SSH tunnel is the access control. Widening a bind address needs a comment
  explaining why.
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
