"""Duplicate a dashboard entry (product or project).

Called by the "duplicate" action in Pages CMS. Reads the Pages CMS payload
from the PAYLOAD environment variable, copies the entry's JSON file, sets the
new names, and writes it next to the original.
"""
import json, os, re, sys
from pathlib import Path

payload = json.loads(os.environ["PAYLOAD"])
ctx, inputs = payload.get("context") or {}, payload.get("inputs") or {}
src = Path(ctx.get("path") or "")
if not src.is_file() or src.suffix != ".json" or not src.parts or src.parts[0] != "content":
    sys.exit(f"Not a content entry: {src}")

data = json.loads(src.read_text(encoding="utf-8"))
title_he = (inputs.get("title_he") or "").strip()
title_en = (inputs.get("title_en") or "").strip()
if title_he:
    data["title_he"] = title_he
if title_en:
    data["title_en"] = title_en
if inputs.get("hide", True) in (True, "true"):
    data["draft"] = True
if isinstance(data.get("order"), (int, float)):
    data["order"] = data["order"] + 1

base = re.sub(r"[^a-z0-9]+", "-", title_en.lower()).strip("-") if title_en else f"{src.stem}-copy"
dest, n = src.with_name(f"{base}.json"), 2
while dest.exists():
    dest, n = src.with_name(f"{base}-{n}.json"), n + 1
dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Created {dest}")
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"dest={dest}\n")
