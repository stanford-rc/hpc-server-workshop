"""Fill SRC-template placeholders. Copies each placeholder's own <a:pPr> so
template spacing/alignment survive; only text, size, weight, and font differ."""
import re, html

MONO = "Courier New"

def esc(s):
    return html.escape(s, quote=False)

def runs_xml(parts, size):
    """parts: list of (text, style) where style in {'', 'b', 'mono', 'bmono'}"""
    out = []
    for text, style in parts:
        attrs = f' lang="en-US" sz="{size}"'
        if "b" in style:
            attrs += ' b="1"'
        face = f'<a:latin typeface="{MONO}"/><a:cs typeface="{MONO}"/>' if "mono" in style else ""
        out.append(f'<a:r><a:rPr{attrs}>{face}</a:rPr><a:t>{esc(text)}</a:t></a:r>')
    return "".join(out)

def set_ph(xml, ph_match, paragraphs, size, space_after=600):
    """Replace the txBody of the <p:sp> whose <p:ph .../> matches ph_match."""
    # locate the sp containing this placeholder
    for m in re.finditer(r'<p:sp>.*?</p:sp>', xml, re.S):
        sp = m.group(0)
        if ph_match not in sp:
            continue
        tb = re.search(r'<p:txBody>(.*?)</p:txBody>', sp, re.S)
        body = tb.group(1)
        # Match a self-closing bodyPr OR a paired one — a naive .*?/> stops at
        # the nested <a:normAutofit/> and truncates the tag.
        bodypr = re.search(
            r'<a:bodyPr[^>]*/>|<a:bodyPr[^>]*>.*?</a:bodyPr>', body, re.S
        ).group(0)
        ppr = re.search(r'<a:pPr.*?</a:pPr>', body, re.S).group(0)
        # space paragraphs apart without touching alignment/indent
        spaced = re.sub(r'<a:spcAft><a:spcPts val="\d+"/></a:spcAft>',
                        f'<a:spcAft><a:spcPts val="{space_after}"/></a:spcAft>', ppr)
        ps = "".join(f'<a:p>{spaced}{runs_xml(parts, size)}</a:p>' for parts in paragraphs)
        new_tb = f'<p:txBody>{bodypr}<a:lstStyle/>{ps}</p:txBody>'
        new_sp = sp.replace(tb.group(0), new_tb)
        return xml.replace(sp, new_sp)
    raise SystemExit(f"placeholder not found: {ph_match}")

def write(slide, edits):
    p = f'unpacked/ppt/slides/{slide}'
    x = open(p).read()
    for ph, paras, size in edits:
        x = set_ph(x, ph, paras, size)
    open(p, 'w').write(x)
    print("filled", slide)

T = lambda s: [(s, "")]
def para(*parts): return list(parts)

# ── 1. Title ────────────────────────────────────────────────────────────────
write('slide1.xml', [
    ('type="ctrTitle"', [T("Running Servers on Sherlock")], 2800),
    ('type="subTitle"', [T("Start one in a session, find it, keep it private, and reach it")], 1400),
])

# ── 2. Three questions ──────────────────────────────────────────────────────
write('slide2.xml', [
    ('type="title"', [T("Three questions, every time")], 2800),
    ('type="body"', [
        para(("Where is it?  ", "b"), ("You don't choose the node, so the server writes its machine and port to a file in $SCRATCH.", "")),
        para(("Who can use it?  ", "b"), ("Any machine on Sherlock can reach it, so every request carries your token.", "")),
        para(("How do I reach it?  ", "b"), ("From Sherlock, ssh to its machine. From your laptop, one SSH tunnel.", "")),
        para(("Every tier answers these three the same way.", "b")),
    ], 1500),
])

# ── 3. The day ──────────────────────────────────────────────────────────────
write('slide6.xml', [
    ('type="title"', [T("The day")], 2800),
    ('type="body"', [
        para(("Morning  ", "b"), ("Tier 1: a data server.  Tier 2: a language model on a GPU.", "")),
        para(("Afternoon  ", "b"), ("Tier 3: tools for Claude (MCP).  Tier 4: a web page for your job.", "")),
        para(("On your own  ", "b"), ("Tier 5: Open OnDemand, with no tunnel.", "")),
        para(("Everything runs in ", ""), ("sh_dev", "mono"), (" sessions, with Sherlock's modules and a shared set of Python packages. Nothing to install.", "")),
    ], 1400),
])

# ── 4. Where (two-column) ───────────────────────────────────────────────────
write('slide4.xml', [
    ('idx="2" type="title"', [T("1. Where is it?")], 2400),
    ('type="title"', [T("The server writes down where it landed")], 1800),
    ('type="body"', [
        para(("$ cat $SCRATCH/hpc_workshop_server.txt", "mono")),
        para(("sh04-18n32.int:44636", "bmono")),
        para(("It picks a free port, so people on the same machine don't clash.", "")),
        para(("To use it from another terminal, ", ""), ("ssh sh04-18n32", "mono"), (" first. You land inside your session's job.", "")),
    ], 1200),
])

# ── 5. Who ──────────────────────────────────────────────────────────────────
write('slide7.xml', [
    ('type="title"', [T("2. Who can use it? The token")], 2800),
    ('type="body"', [
        para(("python3 -c \"import secrets; print(secrets.token_urlsafe(32))\" > ~/.hpc_workshop/token", "mono")),
        para(("chmod 600 ~/.hpc_workshop/token", "mono")),
        para(("Every request sends it; without it the server answers 401.", "")),
        para(("For your lab: ", "b"), ("a group-readable token file in $GROUP_HOME.", "")),
        para(("Ollama has no token, so it only accepts connections from its own machine.", "")),
    ], 1300),
])

# ── 6. Reach ────────────────────────────────────────────────────────────────
write('slide8.xml', [
    ('type="title"', [T("3. How do I reach it from my laptop?")], 2800),
    ('type="body"', [
        para(("One command on your laptop:", "b")),
        para(("ssh -N -L 8080:<machine>:<port> login.sherlock.stanford.edu", "mono")),
        para(("Then open http://localhost:8080. Your laptop's port 8080 now leads to the server.", "")),
        para(("SUNet password and Duo as usual. Ctrl-C closes the tunnel.", "")),
        para(("If your SSH config shares connections (ControlMaster), a closed tunnel can keep the port. ", ""), ("ssh -O exit", "mono"), (" frees it.", "")),
    ], 1400),
])

# ── 7. Tier 2 ───────────────────────────────────────────────────────────────
write('slide9.xml', [
    ('type="title"', [T("Tier 2: a model on a GPU slice")], 2800),
    ('type="body"', [
        para(("sh_dev -g 1 -m 8000", "mono"), ("  one slice of a GPU (6 GB), usually right away", "")),
        para(("Ollama:  ", "b"), ("ml ollama", "mono"), (". Models come from Sherlock's library on Oak; we use gemma3:4b.", "")),
        para(("Your own server:  ", "b"), ("Hugging Face transformers with Qwen2.5-1.5B-Instruct, behind your token.", "")),
        para(("Test models before you trust them. ", "b"), ("Smaller ones made up what SLURM stands for, or turned 4 × 4000 MB into 32000 GB.", "")),
    ], 1400),
])

# ── 8. Tier 3 ───────────────────────────────────────────────────────────────
write('slide10.xml', [
    ('type="title"', [T("Tier 3: tools for Claude")], 2800),
    ('type="body"', [
        para(("MCP lets you give Claude tools. Claude decides which to call.", "b")),
        para(("The server offers three: list, search and read a folder of documents. No GPU needed.", "")),
        para(("Claude Code runs on Sherlock too: ", ""), ("ml claude-code", "mono"), (", signed in with your Stanford account.", "")),
        para(("On Sherlock, Claude already reads Sherlock's own guidance, so it uses your tools when the question needs them. Questions and tool results go to Anthropic.", "")),
    ], 1400),
])

# ── 9. Tier 4 (two-column) ──────────────────────────────────────────────────
write('slide12.xml', [
    ('idx="2" type="title"', [T("Tier 4")], 2400),
    ('type="title"', [T("A web page for your job")], 1800),
    ('type="body"', [
        para(("upload an input  →  run the job  →  download the results", "b")),
        para(("One server sends both the page and the data behind it, so there's nothing extra to set up.", "")),
        para(("Paste your token into the page once; the browser keeps it as a cookie, so plain download links work.", "")),
        para(("The job only reads inputs/ and writes results/. Your own script can take its place.", "")),
    ], 1100),
])

# ── 10. Running it for real (two-column) ────────────────────────────────────
write('slide13.xml', [
    ('idx="2" type="title"', [T("After today")], 2400),
    ('type="title"', [T("Running it for real")], 1800),
    ('type="body"', [
        para(("Longer than a session: ", "b"), ("mkdir -p logs; sbatch submit_server.sh", "mono"), (". Batch jobs go to normal or gpu, not dev, and may wait in the queue.", "")),
        para(("Your own packages: ", "b"), ("uv venv and uv pip install --no-build in $GROUP_HOME. Plain python on Sherlock is Python 2; use python3.", "")),
        para(("Your own data: ", "b"), ("swap the table, the model, the documents or the job. The session, address file, token and tunnel stay the same.", "")),
    ], 1000),
])

# ── 11. Where next ──────────────────────────────────────────────────────────
write('slide11.xml', [
    ('type="title"', [T("Where to go next")], 2800),
    ('type="body"', [
        para(("No tunnel at all?  ", "b"), ("Tier 5: an OnDemand session is already inside Sherlock.", "")),
        para(("Keep the token.  ", "b"), ("Don't put research data behind a server anyone on Sherlock can query.", "")),
        para(("Not on the public internet.  ", "b"), ("The way in from outside is SSH with your SUNet ID and Duo.", "")),
        para(("Something shared and long-running?  ", "b"), ("That needs a proper service: talk to SRCC.", "")),
    ], 1400),
])
