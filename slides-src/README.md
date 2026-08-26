# Deck source

`../HPC-Server-Workshop.pptx` is generated from the SRC branded template, not
hand-edited. To change a slide, edit `fill.py` and rebuild — hand-editing the
`.pptx` means the next rebuild silently discards your change.

```bash
# The SRC branded template is not redistributed here — point at your own copy.
cp "$SRC_THEME" template.pptx        # e.g. export SRC_THEME="~/path/SRC Theme.pptx"
SKILL=<path to the pptx skill dir> ./build.sh
cp HPC-Server-Workshop.pptx ../
```

Attendees don't need any of this — the built `.pptx` is committed. This is only
for whoever maintains the slides.

`build.sh` unpacks the template, clones the layouts it needs, sets slide order,
then `fill.py` writes text into the template's own placeholders so fonts,
colors, and layouts are inherited rather than restated.

Slide order lives in the `order` list in `build.sh`; slide content lives in
`fill.py`, one `write()` call per slide.
