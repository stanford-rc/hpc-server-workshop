# Software modules

Sherlock uses Lmod. Software is not on your `PATH` until you load it.

| Command | What it does |
|---------|--------------|
| `ml spider <name>` | Search for available versions of a package |
| `ml <name>` | Load the default version |
| `ml <name>/<version>` | Load a specific version |
| `ml list` | Show what you currently have loaded |
| `ml purge` | Unload everything |
| `ml save <label>` | Save the current set as a named collection |

## In batch scripts

Always load modules explicitly inside your sbatch script. A batch job does
not inherit the modules from your login shell, so a script that works
interactively can fail in the queue.

```bash
module load python/3.12.1
module load pytorch/2.3
```

## Python packages

Prefer a virtual environment on top of a loaded Python module rather than
`pip install --user`, which leaks packages across projects and Python
versions.
