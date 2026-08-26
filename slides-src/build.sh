#!/bin/bash
# Rebuild HPC-Server-Workshop.pptx from the SRC template.
#   SKILL=<path to pptx skill dir> ./build.sh
set -euo pipefail
SK="${SKILL:?set SKILL to the pptx skill directory}"
rm -rf unpacked && python3 -c "import zipfile; zipfile.ZipFile('template.pptx').extractall('unpacked')"
# 6 extra title+body slides, 2 extra two-column slides (aside + tip)
for i in 1 2 3 4 5 6; do python3 "$SK/scripts/add_slide.py" unpacked/ slide2.xml >/dev/null; done
python3 "$SK/scripts/add_slide.py" unpacked/ slide4.xml >/dev/null
python3 "$SK/scripts/add_slide.py" unpacked/ slide4.xml >/dev/null
python3 - <<'PY'
import re
p='unpacked/ppt/presentation.xml'; x=open(p).read()
order=['rId5','rId6','rId10','rId8','rId11','rId12','rId13','rId14','rId16','rId17','rId15']
new='<p:sldIdLst>'+''.join(f'<p:sldId id="{256+i}" r:id="{r}"/>' for i,r in enumerate(order))+'</p:sldIdLst>'
open(p,'w').write(re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>', new, x, flags=re.S))
PY
python3 "$SK/scripts/clean.py" unpacked/ >/dev/null
python3 fill.py
rm -f HPC-Server-Workshop.pptx && (cd unpacked && zip -qXr ../HPC-Server-Workshop.pptx .)
python3 "$SK/scripts/office/validate.py" HPC-Server-Workshop.pptx --original template.pptx
