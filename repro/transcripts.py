#!/usr/bin/env python3
"""§D's linked conversation transcripts. Tier A.

The manuscript links to `transcripts/<name>.json` beside itself for the full
text of the conversations it excerpts. Those files are extracts of data/runs/,
so they are built here rather than maintained by hand, and verified rather than
trusted: each must still be byte-identical to its source conversation, and each
passage the paper quotes must appear in it verbatim.

    python3 repro/transcripts.py            # verify
    python3 repro/transcripts.py --write    # (re)build paper/transcripts/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
OUT = REPO / "paper" / "transcripts"


def declared() -> list[dict]:
    return json.loads((DATA / "transcripts.json").read_text(encoding="utf-8"))["transcripts"]


def source(t: dict) -> Path:
    return (DATA / "runs" / t["run"] / "transitions" / t["transition"] /
            "conversations" / f"{t['conversation']}.json")


def verify() -> tuple[bool, str]:
    """Every declared transcript exists, matches its source, and carries its quotes."""
    problems = []
    for t in declared():
        src, dst = source(t), OUT / f"{t['name']}.json"
        if not src.exists():
            problems.append(f"{t['name']}: source {src.relative_to(REPO)} is gone")
            continue
        if not dst.exists():
            problems.append(f"{t['name']}: not extracted; run transcripts.py --write")
            continue
        raw = src.read_bytes()
        if hashlib.sha256(raw).hexdigest() != hashlib.sha256(dst.read_bytes()).hexdigest():
            problems.append(f"{t['name']}: extract differs from its source conversation")
            continue
        text = raw.decode("utf-8", "replace")
        for q in t.get("quoted", ()):
            if q not in text:
                problems.append(f"{t['name']}: the paper quotes a passage it does not contain "
                                f"({q[:50]!r})")
    if problems:
        return False, "; ".join(problems)
    return True, f"{len(declared())} transcripts match their source conversations"


def links_are_declared(paper_text: str) -> tuple[bool, str]:
    """Every transcripts/ link in the manuscript is one we ship."""
    import re
    linked = set(re.findall(r"transcripts/([A-Za-z0-9_-]+)\.json", paper_text))
    names = {t["name"] for t in declared()}
    missing, extra = linked - names, names - linked
    if missing:
        return False, f"the paper links to undeclared transcripts: {sorted(missing)}"
    if extra:
        return False, f"declared but never linked: {sorted(extra)}"
    return True, f"{len(linked)} links resolve"


def write() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for t in declared():
        src = source(t)
        if not src.exists():
            raise SystemExit(f"{t['name']}: source {src.relative_to(REPO)} is gone")
        (OUT / f"{t['name']}.json").write_bytes(src.read_bytes())
        print(f"  {t['name']}.json  <- {src.relative_to(DATA)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="(re)build paper/transcripts/")
    args = ap.parse_args()
    if args.write:
        return write()
    ok, msg = verify()
    print(f"{'OK' if ok else 'FAILED'}: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
