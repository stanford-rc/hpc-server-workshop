# HPC Server Workshop

How to run a **server** on Sherlock, and use it from a program, an AI
assistant or your laptop's browser.

## Why servers, and why now

Most cluster jobs start, do their work and stop. A **server** is different: it
loads something once (a table, a model, a set of documents) and then waits for
questions, so you can ask it many things without paying the loading cost each
time.

More and more researchers are asking us how to run one, and AI seems to be a
large part of the reason:

- **AI produces a lot of results to work through.** A model can label
  thousands of images or summarize thousands of documents in one run. Instead
  of reading through the output files, you often want to search, filter and
  ask questions of the results, and a server keeps them loaded and ready for
  that.
- **Language models are used through servers.** Chatbots work this way: the
  model is loaded once, and prompts are sent to it. Running a model on
  Sherlock's GPUs means running a server.
- **AI assistants reach your data through servers.** An assistant like Claude
  can use tools you give it, and those tools are offered by a server (Tier 3).

A server on Sherlock also keeps your work next to your data. Large results,
models and datasets stay on Sherlock, and you send questions to them instead
of copying them to your laptop.

## What's different about a server on Sherlock

Most servers, like the ones behind websites, run all the time on machines set
aside for them. On Sherlock they can't:

- Everything runs as a **job**, with a time limit, on shared machines. A server
  runs while your session or job does, and stops when it ends.
- You don't choose which machine you get, or which port is free on it, so the
  server has to tell you where it is.
- Other people use the same machines, and any of them could connect to your
  server, so it needs a password (a **token**).
- The machines can't be reached from outside Sherlock, so you reach your
  server from your laptop through an SSH connection.

So a server on Sherlock isn't always on, but it can be **always available**:
the scripts are ready, and you start the server when you sit down to work and
stop it when you're done. Each point above is one of the pieces in "How every
tier works" below, and this workshop shows how to handle each one.

## Schedule

| Session | Tiers | What you'll do |
|---|---|---|
| Morning, 1 hour | [1: Data server](01-data-server/) | Serve a table; find it with an address file; protect it with a token; see it in your browser |
| | [2: Model server](02-model-server/) | Serve a language model on a GPU, with Ollama and with your own server |
| Afternoon, 1 hour | [3: MCP server](03-mcp-server/) | Give Claude tools that search a folder of documents |
| | [4: Web page](04-web-gui/) | Upload an input, run a job and download the results from your browser |
| On your own | [5: Open OnDemand](05-ood-access/) | Use a server from Sherlock's in-browser apps, with no tunnel |

## Before you start

You need:

- **A Sherlock account**, and to be able to log in from your laptop with
  `ssh <SUNetID>@login.sherlock.stanford.edu` (SUNet password and Duo).
- **A terminal on your laptop** for the tunnels: Terminal on macOS, PowerShell
  on Windows.

Nothing to install: everything runs on Sherlock, using Sherlock's modules and a
shared set of Python packages made for the workshop.

Get the workshop files, in a Sherlock terminal:

```bash
cd ~
git clone https://github.com/stanford-rc/hpc-server-workshop.git
```

## How every tier works

The same few pieces appear in every tier:

1. **An interactive session.** Servers don't run on login nodes. `sh_dev` gives
   you a session on a compute node, usually right away, for an hour by default.
   Sherlock lets you have two `dev` sessions at once.
2. **The server picks a free port and writes down where it is.** You don't
   choose which compute node you get, and many people share each one, so the
   server writes `<machine>:<port>` to an **address file** in `$SCRATCH`, your
   scratch space, which every Sherlock machine can read.
3. **A token keeps everyone else out.** Any machine on Sherlock can reach a
   server, so every request must include your **token**, a long random password
   in `~/.hpc_workshop/token` that only you can read. Whoever can read that file
   can use the server; Tier 1 shows how to share it with your lab. (Ollama, in
   Tiers 2 and 4, has no token, so it only accepts connections from its own
   machine.)
4. **More terminals on the same machine.** To run a client next to your server,
   open another Sherlock terminal and `ssh <machine>`. You land inside your
   session's job, with its CPU and memory.
5. **An SSH tunnel to reach it from your laptop.** One command on your laptop,
   `ssh -S none -N -L 8080:<machine>:<port> login.sherlock.stanford.edu`, makes
   http://localhost:8080 in your browser lead to the server.

Each tier's scripts load what they need: `module load python/3.12.1`, then the
workshop's shared Python packages
(`/home/groups/sh_support/bcritt/server_workshop/venv`). The `#SBATCH` lines at
the top of each script are only used if you submit it as a batch job, which is
how you'd run a server for a working session longer than `sh_dev` allows.

## Making your own environment

The shared packages are for the workshop. For your own projects, make your own
set of Python packages in your group's space (`$HOME` is only 15 GB), from
inside an `sh_dev` session. Each tier lists what it needs in
`requirements.txt`:

```bash
module load python/3.12.1 uv/0.10.8
uv venv --python "$(command -v python3)" $GROUP_HOME/$USER/myenv
uv pip install --python $GROUP_HOME/$USER/myenv/bin/python --no-build --no-cache -r requirements.txt
```

Then change the `source ...` line in that tier's scripts to
`source $GROUP_HOME/$USER/myenv/bin/activate`.

- Use `python3`, not `python`: on Sherlock, plain `python` is the old system
  Python 2.
- `--no-build` makes uv use only ready-made packages. Sherlock's operating
  system is too old for the newest builds of some packages (numpy and torch,
  for example); without this flag the install tries to compile them from source
  and fails after several minutes.
- `--no-cache` keeps the downloads out of `~/.cache`, which otherwise eats into
  your `$HOME` quota.

## When something doesn't work

| What you see | Likely cause |
|---|---|
| A client waits, then "did not respond" | The server isn't running, or stopped and left its old address file behind. Start it again |
| `401` / "refused the token" | The request didn't include your token, or the token file changed after the server started |
| `Access denied by pam_slurm_adopt` when you `ssh <machine>` | You don't have a session on that machine (it ended, or the name is wrong) |
| The tunnel prints "Address already in use" | Another tunnel is using laptop port 8080. Close it (if your SSH config uses `ControlMaster`, `ssh -O exit login.sherlock.stanford.edu`), or use 8081 and http://localhost:8081 |
| `python: No module named venv` | You ran `python`, which is Python 2 on Sherlock. Use `python3` |
