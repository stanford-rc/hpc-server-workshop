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
    ('type="subTitle"', [T("Five tiers of one SLURM pattern — from a REST API to a browser GUI")], 1400),
])

# ── 2. Two problems ─────────────────────────────────────────────────────────
write('slide2.xml', [
    ('type="title"', [T("Two problems, every single time")], 2800),
    ('type="body"', [
        para(("Where is it?  ", "b"), ("SLURM picks the node, so you cannot hardcode a hostname. The server writes its own address to a file in $SCRATCH; clients read that file.", "")),
        para(("How do I reach it?  ", "b"), ("A compute node is not reachable from your laptop. You either forward a port to it, or use a browser that is already inside the cluster.", "")),
        para(("Everything here is those two problems, solved the same way five times.", "b")),
    ], 1500),
])

# ── 3. Five tiers ───────────────────────────────────────────────────────────
write('slide2.xml'.replace('2', '6'), [
    ('type="title"', [T("The five tiers")], 2800),
    ('type="body"', [
        para(("01  Data server  ", "b"), ("— serve a CSV over REST.  Any compute node.", "")),
        para(("02  Model server  ", "b"), ("— ml ollama on an instant MIG slice.", "")),
        para(("03  MCP server  ", "b"), ("— give Claude structured tool access.  No GPU.", "")),
        para(("04  Web GUI  ", "b"), ("— drive a job from your laptop's browser.  Any node.", "")),
        para(("05  OnDemand  ", "b"), ("— the same, in-browser, with no tunnel at all.", "")),
        para(("Each is self-contained. The discovery and tunnel patterns are identical in all five.", "")),
    ], 1400),
])

# ── 4. Discovery (two-column) ───────────────────────────────────────────────
write('slide4.xml', [
    ('idx="2" type="title"', [T("1. Discovery")], 2400),
    ('type="title"', [T("The server writes down where it landed")], 1800),
    ('type="body"', [
        para(("$ cat $SCRATCH/hpc_workshop_gui.txt", "mono")),
        para(("sh03-01n52:41235", "bmono")),
        para(("An ephemeral port, so two people on one node don't collide.", "")),
        para(("<node>:<port> is the format the Sherlock Ollama docs use — both halves pull straight back out with shell expansion.", "")),
    ], 1200),
])

# ── 5. The tunnel ───────────────────────────────────────────────────────────
write('slide7.xml', [
    ('type="title"', [T("2. The tunnel — where everyone trips")])if False else ('type="title"', [T("2. The tunnel — where everyone trips")], 2800),
    ('type="body"', [
        para(("The bind address and the tunnel target must agree.", "b")),
        para(("Server on 127.0.0.1  →  ", ""), ("ssh -NfL 8080:localhost:PORT NODE", "mono")),
        para(("      Encrypted end to end. Needs a running job on that node.", "")),
        para(("Server on 0.0.0.0  →  ", ""), ("ssh -NfL 8080:NODE:PORT login.sherlock", "mono")),
        para(("      Works without node access, but the last hop is cleartext internally.", "")),
        para(("Then open http://localhost:8080 — localhost, not the node name.", "")),
    ], 1400),
])

# ── 6. Tier 4 ───────────────────────────────────────────────────────────────
write('slide8.xml', [
    ('type="title"', [T("Tier 4 — a page you actually wrote")], 2800),
    ('type="body"', [
        para(("upload an input  →  job runs on the cluster  →  download the output", "b")),
        para(("The page and the API come from one FastAPI app. Same origin, so there is no CORS to configure, no second web server, and no build step.", "")),
        para(("Serve them separately and you hit cross-origin errors immediately — which is when people start pasting wildcard CORS onto an unauthenticated server.", "")),
        para(("Point RESULTS_DIR at a directory your pipeline already writes to and the page lists those files with no code changes.", "")),
    ], 1400),
])

# ── 7. Tier 5 ───────────────────────────────────────────────────────────────
write('slide9.xml', [
    ('type="title"', [T("Tier 5 — OnDemand, no tunnel")], 2800),
    ('type="body"', [
        para(("An OOD session already runs on a compute node. The browser is inside the cluster, so nothing needs forwarding.", "b")),
        para(("Jupyter, code-server, RStudio, TensorBoard, Interactive Desktop, and a file browser — all there, no code required.", "")),
        para(("For \"I just want my results on my laptop,\" the Files menu already does it.", "")),
        para(("To let your lab launch your own tool from the dashboard, you package it as a custom interactive app — that one needs SRCC.", "")),
    ], 1400),
])

# ── 8. Tier 3 MCP ───────────────────────────────────────────────────────────
write('slide10.xml', [
    ('type="title"', [T("Tier 3 — MCP: tools here, model there")], 2800),
    ('type="body"', [
        para(("You expose tools. Claude decides which to call.", "b")),
        para(("Ask \"how do I stop hitting my quota?\" and it picks search_docs, then read_doc, and answers from what it finds. You never name an endpoint.", "")),
        para(("No GPU, and no model on the cluster — this process reads files and matches strings. The tools and the model are separate services; that is the point of MCP.", "")),
        para(("Streamable HTTP is ordinary HTTP, so it forwards through the very same tunnel as tier 4.", "")),
    ], 1400),
])

# ── 9. ASIDE — private options (two-column) ─────────────────────────────────
write('slide12.xml', [
    ('idx="2" type="title"', [T("Aside")], 2400),
    ('type="title"', [T("Keeping it all on Sherlock")], 1800),
    ('type="body"', [
        para(("Tier 3's default sends your prompts and the retrieved text to Anthropic.", "")),
        para(("To keep it inside Stanford, run the model here too: ", ""), ("ml ollama", "mono"), (" on a GPU node — the same service pattern as tier 2, endpoint in ~/.ollama_server.", "")),
        para(("Then either point a CLI agent at it (OpenCode, Crush and pi all take an OpenAI-compatible base_url), or forward two ports and drive it from a local editor.", "")),
        para(("Caveat: ", "b"), ("small local models are markedly worse at multi-step tool calling, and Ollama caps context at 4k under 24 GB of GPU memory — raise num_ctx first or agents simply fail.", "")),
    ], 1100),
])

# ── 10. TIP — HuggingFace instead of Ollama (two-column) ────────────────────
write('slide13.xml', [
    ('idx="2" type="title"', [T("Tip")], 2400),
    ('type="title"', [T("When you want HuggingFace instead")], 1800),
    ('type="body"', [
        para(("The headline: pre-tuned, domain- and task-specific models.", "b")),
        para(("The Hub carries models already tuned for a field or a task — scientific text, biomedical literature, protein sequences — that Ollama's library doesn't have. A model that knows your domain usually beats a bigger general one, on less GPU.", "")),
        para(("Also for gated models, quantization you control, and reproducible batch inference.", "")),
        para(("What changes: ", "b"), ("you write the server; ", ""), ("module load pytorch", "mono"), (" rather than pip-installing torch; set ", ""), ("HF_HOME=$SCRATCH/hf_cache", "mono"), (" or you re-download weights every job; ask for a full GPU, not a MIG slice. And if the model is an encoder, change the pipeline task — text-generation is the wrong one.", "")),
        para(("Tier 2 in the repo ships both paths, scripts included.", "b")),
    ], 1000),
])

# ── 10. Where to start ──────────────────────────────────────────────────────
write('slide11.xml', [
    ('type="title"', [T("Where to start")], 2800),
    ('type="body"', [
        para(("Never run a server in a batch job?  ", "b"), ("Tier 1. The SLURM patterns there are identical in all five tiers.", "")),
        para(("Already have results you want to see?  ", "b"), ("Tier 5 — it needs no code at all.", "")),
        para(("Want a page of your own?  ", "b"), ("Tier 4, then tier 3 once you'd rather ask questions than click.", "")),
        para(("One warning: none of these servers authenticate anyone. The SSH tunnel is doing that job — keep them on loopback and off public ports.", "")),
    ], 1400),
])
