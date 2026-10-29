# Tier 1: A data server

Most jobs on a cluster start, do their work and stop. Sometimes you'd rather
keep something loaded and ask it questions again and again: a big table, a
search index, a model that takes minutes to load. A **server** is a program
that does that. It loads the thing once, then waits for questions and answers
each one.

Here you'll run a small one. It loads a table of made-up cluster jobs
(`data/jobs.csv`, 20 rows) and answers questions like "which jobs failed?" or
"what's the average memory use?". Along the way you'll use the pieces every
tier in this workshop relies on:

- an **interactive session** on a compute node, where the server runs
- an **address file**, so other programs can find the server
- a **token**, so only you (or your lab) can use it
- an **SSH tunnel**, to reach it from a browser on your laptop

## Files

| File | What it is |
|------|------------|
| `server.py` | The server. Loads `data/jobs.csv` and answers at `/jobs`, `/stats`, `/health` |
| `client.py` | A small program that finds the server and asks it some questions |
| `submit_server.sh` | Starts the server (inside a session, or as a batch job) |
| `submit_client.sh` | Runs the client |
| `data/jobs.csv` | The sample data (made up) |

## 1. Log in to Sherlock

In a terminal on your laptop, with your SUNet ID in place of `<SUNetID>`:

```bash
ssh <SUNetID>@login.sherlock.stanford.edu
```

Enter your SUNet password and approve the Duo prompt. You're now on a **login
node**, the shared machine everyone lands on first. If you don't have the
workshop files yet, get them:

```bash
cd ~
git clone https://github.com/stanford-rc/hpc-server-workshop.git
```

## 2. Make your token (once)

A server on a compute node can be reached from any other machine on Sherlock.
To keep everyone else out, every request has to include a **token**: a long
random password that only you have. Make one now, on the login node:

```bash
ml purge
ml python/3.12.1
mkdir -p ~/.hpc_workshop
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > ~/.hpc_workshop/token
chmod 600 ~/.hpc_workshop/token
ls -l ~/.hpc_workshop/token
```

`ml` is short for `module load`: Sherlock keeps software in **modules**.
`ml purge` unloads any you already had, so you start clean, and
`ml python/3.12.1` makes Python 3.12 available. `ls -l` should show
`-rw-------`: you can read the file and nobody else can.
That's what `chmod 600` does, and it's the whole lock: whoever can read this
file can use your servers. Every tier in the workshop uses this same file.

> **Sharing with your lab.** To let your lab use a server, keep the token in a
> file your group can read instead, for example
> `$GROUP_HOME/<your project>/token` with `chmod 640`, and point the server and
> your labmates' clients at it with `export TOKEN_FILE=<that path>`. Anyone in
> the group can then use the server, and nobody else can. To add specific
> people outside the group, give them read access to the file with an ACL
> (`setfacl`). Don't put research data behind a server without a token.

## 3. Start a session and the server

Servers don't run on login nodes. Ask for an **interactive session** on a
compute node instead:

```bash
sh_dev
```

`sh_dev` gives you one CPU core, 4 GB of memory and one hour on Sherlock's
`dev` machines, which usually start right away. Your prompt changes to show
the compute node's name, for example `sh04-18n32`.

Then start the server:

```bash
cd ~/hpc-server-workshop/01-data-server
bash submit_server.sh
```

`submit_server.sh` loads Sherlock's Python (`module load python/3.12.1`) and
the workshop's shared Python packages, then runs `server.py`. The first start
can take about 30 seconds while Python loads its packages. When it's ready it
prints something like:

```
Loaded 20 job records.
Listening on 0.0.0.0:44636 on sh04-18n32.int
Address written to /scratch/users/<you>/hpc_workshop_server.txt
```

Leave it running in this terminal. To stop it later, press **Ctrl-C**.

Three things just happened:

- **It loaded the data, once.** `data/jobs.csv` is a small made-up table of 20
  past cluster jobs, one row per job (the 20 records in the message). The first
  few rows:

  ```
  job_id,user,partition,cluster,nodes,cpus,mem_gb,runtime_hours,status,submit_time
  1001,alice,normal,sherlock,1,8,32,2.5,completed,2024-01-15 09:00:00
  1002,bob,gpu,sherlock,1,4,16,0.8,failed,2024-01-15 10:30:00
  1003,carol,normal,sherlock,2,16,64,6.2,completed,2024-01-15 11:00:00
  ```

  The server read it into memory when it started and keeps it there, so every
  question after this is answered from memory without reading the file again.
  That's the point of a server. With 20 rows it hardly matters; with a big
  dataset or a model that takes minutes to load, it matters a lot.
- **It picked a free port.** A **port** is a numbered "door" on a machine that
  a server listens at. Many people share each compute node, so a fixed number
  like 8080 would clash with someone else's. Instead the server asks the system
  for any free one (44636 above; yours will differ).
- **It wrote down where it is.** You don't choose which compute node you get,
  so the server writes `<machine>:<port>` to an **address file** in your
  scratch space (`$SCRATCH`), which every Sherlock machine can read.

## 4. Ask it questions

Open a **second terminal** on Sherlock. It starts on a login node, so first
log in to the machine your session is on. Find its name in your first
terminal: it's in the session's prompt (`[<you>@sh04-18n32 ~]$`) and in the
server's `Listening on ... on sh04-18n32.int` line. Yours will be different.
Put it in place of `<machine>`:

```bash
ssh <machine>
```

That puts you inside your session's job, sharing its core and memory. It's a
new terminal, though, so modules you loaded in the other one aren't loaded
here. Load Python again, then start it with the workshop's packages:

```bash
ml python/3.12.1
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate
python3
```

In Python, read where the server is and your token:

```python
import os, requests
url = "http://" + open(os.path.expandvars("$SCRATCH/hpc_workshop_server.txt")).read().strip()
headers = {"x-token": open(os.path.expanduser("~/.hpc_workshop/token")).read().strip()}
```

Now ask it things, one line at a time. Each answer comes straight back, because
the server already has the table loaded:

```python
requests.get(f"{url}/stats", headers=headers).json()
requests.get(f"{url}/jobs", params={"status": "failed"}, headers=headers).json()
requests.get(f"{url}/jobs/1004", headers=headers).json()
```

`requests.get` sends one question to the server, with your token attached, and
`.json()` turns the answer into Python lists and dictionaries. Each kind of
question has its own **endpoint**, a path like `/stats` added to the end of the
server's address:

| Endpoint | What it answers |
|---------|-----------------|
| `/stats` | Totals and averages across all jobs |
| `/jobs` | Job records. Filters: `cluster`, `status`, `limit` |
| `/jobs/<id>` | One job by its ID |
| `/health` | Whether the server is up |

**Your turn:** which Farmshare jobs completed? (Hint:
`params={"cluster": "farmshare", "status": "completed"}`.) Then ask for just the
first three jobs.

Type `exit()` to leave Python when you're done.

## 5. Look at it from your laptop

FastAPI, the toolkit `server.py` is built with, makes a web page that lists
every endpoint and lets you try them. To see it in your laptop's browser you
need an **SSH tunnel**: an SSH connection that carries a port on your laptop
through to the server.

Get the server's address in a Sherlock terminal:

```bash
cat $SCRATCH/hpc_workshop_server.txt
```

Then, in a terminal **on your laptop**, put that machine name and port in place
of `<machine>` and `<port>`:

```bash
ssh -N -L 8080:<machine>:<port> login.sherlock.stanford.edu
```

It asks for your SUNet password and Duo, then seems to hang. That's correct:
`-N` means "don't open a shell, just carry the connection", and `-L` means
"connect port 8080 on this laptop to `<machine>:<port>` on Sherlock". Leave it
running; **Ctrl-C** closes the tunnel.

Now open **http://localhost:8080/docs** in your browser. Click **Authorize**,
paste your token (`cat ~/.hpc_workshop/token` in a Sherlock terminal shows it),
then open `/stats`, click **Try it out**, then **Execute**.

## 6. Stop

Press Ctrl-C in the server's terminal, then type `exit` to leave the session
(or let the hour run out). Ctrl-C in the laptop terminal closes the tunnel.

## Tip: asking from a script

A program can ask the same questions. `bash submit_client.sh` runs `client.py`,
which asks three and prints the answers. That's how a batch job or a pipeline
would use a server.

## Running it for real

In the workshop the server runs inside `sh_dev`, which lasts at most two hours.
For a server you want to keep running longer, submit the same script as a
**batch job**, which runs without you:

```bash
mkdir -p logs           # the job's printed output goes here
sbatch submit_server.sh
```

The `#SBATCH` lines at the top of the script say what the job asks for, with a
comment on each. Batch jobs can't run on `dev`, so this one goes to Sherlock's
standard machines and may wait in the queue first. Everything else works the
same: the address file, the token and the tunnel.

## Your own Python packages

The workshop uses one shared, ready-made set of Python packages. To make your
own for your projects, see "Making your own environment" in the
[top-level README](../README.md#making-your-own-environment).

## Using your own data

Swap `data/jobs.csv` for your own table, and change the endpoints in
`server.py` (the functions under each `@app.get(...)` line) to the questions you
want to ask. The session, address file, token
and tunnel stay the same.
