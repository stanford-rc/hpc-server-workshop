# Tier 4: A web page for your job

Put a simple web page in front of a job, and use it from your laptop's
browser: upload an input file, run the job on Sherlock, and download what it
produced. This tier answers "can I build a small site to work with my research
data?"

Here the job sends a list of prompts to the Ollama model from Tier 2 and saves
the answers. The page and the job don't care what the job does, so the same
setup works for your own analysis.

```
  your laptop               SSH tunnel             Sherlock
 ┌──────────────┐                          ┌───────────────────────────┐
 │   browser    │ ── upload prompts ─────▶ │ web server     inputs/    │
 │ localhost    │                          │                   │       │
 │   :8080      │                          │ predict.py ◀──────┘       │
 │              │                          │     │  ──▶ Ollama (Tier 2)│
 │              │ ◀── download results ─── │ results/ ◀┘               │
 └──────────────┘                          └───────────────────────────┘
```

## Files

| File | What it is |
|------|------------|
| `server.py` | The web server. Serves the page and the files behind it |
| `static/index.html` | The whole page: plain HTML and a little JavaScript |
| `predict.py` | The job: reads `inputs/`, asks the model, writes `results/` |
| `submit_server.sh` | Starts the web server |
| `submit_job.sh` | Runs the job |
| `inputs/` | Where uploads go |
| `results/` | What the page offers for download (starts with a sample) |

## 1. Start the model (session 1)

The job needs a model to talk to. Start Ollama as in Tier 2:

```bash
sh_dev -g 1 -m 8000
ml ollama
cd ~/hpc-server-workshop/02-model-server
bash submit_ollama.sh
```

Note the machine name in this session's prompt; you'll need it in step 4.
Leave it running.

## 2. Start the web server (session 2)

In a second Sherlock terminal:

```bash
sh_dev
cd ~/hpc-server-workshop/04-web-gui
bash submit_server.sh
```

That's two sessions, the most `dev` allows at once. When it's ready it prints
the tunnel command, for example:

```
Web server on sh04-18n32.int:39831
...
On your laptop, open the tunnel (leave it running):
  ssh -S none -N -L 8080:sh04-18n32.int:39831 login.sherlock.stanford.edu
then open http://localhost:8080 and paste your token into the page.
```

## 3. Open the page (on your laptop)

Copy the `ssh -S none -N -L ...` line into a terminal **on your laptop** and sign in
with your SUNet password and Duo. Leave it running, as in Tier 1.

Open **http://localhost:8080**. The page says "paste your token above and press
Save". Show your token in a Sherlock terminal with `cat ~/.hpc_workshop/token`,
paste it into the Token box and press **Save**. The page now shows
"connected", lists the sample results, and lists `inputs/`.

The token works the same way as in the other tiers: the server refuses
everything except the page itself without it. Pressing Save stores it in your
browser as a **cookie**, a small value the browser sends back to this site with
every request. That's what lets the plain "download" links work too.

Now make a file on your laptop called `prompts.txt` with one question per line,
for example:

```
What is a compute node, in one sentence?
Why write job output to scratch storage?
```

and upload it with **Choose file** and **Upload**.

## 4. Run the job (a terminal on the model's machine)

Ollama only accepts connections from its own machine, so the job has to run
there. Open a third Sherlock terminal, log in to session 1's machine, and run
the job on your upload:

```bash
ssh <session 1 machine>
cd ~/hpc-server-workshop/04-web-gui
bash submit_job.sh prompts.txt
```

```
Input: prompts.txt (2 prompts)
  [1/2] 'What is a compute node, in one sentence?' -> 242 chars
  [2/2] 'Why write job output to scratch storage?' -> 291 chars

Wrote prompts_20261028-081653.jsonl and prompts_20261028-081653.csv to .../04-web-gui/results
```

In testing, two prompts took about 10 seconds. If you run it from the wrong
machine, it tells you which machine to `ssh` to.

## 5. Download the results

Press **Refresh** on the page. The new `.csv` and `.jsonl` files are at the top;
click **download** to save one to your laptop. The `.csv` opens in a
spreadsheet program: one row per prompt, with the model's answer next to it.

## 6. Stop

Ctrl-C in each session's terminal, then `exit` both sessions, and Ctrl-C the
tunnel on your laptop.

## How it fits together

- **One server for the page and the data.** `server.py` sends the page itself
  at `/` and the data behind it at `/api/...`. Because both come from the same
  address, the browser treats them as one site, and there's nothing extra to
  set up.
- **The job knows nothing about the web.** `predict.py` only reads `inputs/` and
  writes `results/`; the web server only lists and moves files in those folders.
  Your own existing script can take `predict.py`'s place unchanged.
- **Uploads can't escape `inputs/`.** `server.py` strips folder names from
  uploaded file names, so a name like `../../.ssh/authorized_keys` can't write
  anywhere else.

## Security

- **Keep the token.** Without it, anyone on Sherlock could reach this server,
  read your results and upload files. With it, only people who can read your
  token file can. For a lab, share the token through a group-readable file, as
  described in Tier 1.
- **Don't try to put this on the public internet.** The only way in from
  outside is an SSH tunnel with your SUNet ID and Duo, and that's how it should
  stay. A service that many people use over a long time needs a proper server,
  and that's a conversation with SRCC.

## Running it for real

Both scripts also work as batch jobs (`mkdir -p logs`, then `sbatch
submit_server.sh` and `sbatch submit_job.sh`). A batch job lands on whatever
machine Slurm picks, so it can't reach an Ollama that only accepts connections
from its own machine. For batch jobs, use the transformers server from Tier 2
instead, which works from any machine with your token: in `submit_job.sh`,
switch the `MODEL_API` and `MODEL_ADDR_FILE` lines to the commented-out
`generate` ones.

## Using your own results

Point `RESULTS_DIR` in `submit_server.sh` at the folder your pipeline already
writes to, and the page lists those files without any changes to `server.py`.
To show a chart or a table instead of a file list, add an endpoint to
`server.py` that returns the numbers, and draw them in `index.html`.
