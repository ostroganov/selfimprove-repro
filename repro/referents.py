#!/usr/bin/env python3
"""§4.6 referent counts: how often the prompts name the user, and the human.

Reproduces the published 2,131 user and 187 human distinct sentences (and 78
generic), over all 54 runs and every committed level.

The unit is a sentence, deduplicated within a run: a self-authored prompt is
mostly carried forward level to level, so counting raw occurrences would count
one unchanged sentence once per level and score long runs by their length
rather than their content. Deduplication is per run and per referent, on the
sentence lowercased with any bullet marker stripped.

    python3 repro/referents.py
    python3 repro/referents.py --raw          # also show undeduplicated counts
    python3 repro/referents.py --by-model

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from themes import word_pattern  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

REPORTED_CORPUS = "all-54"
REPORTED_SET = "referents.v1"
PUBLISHED = {"user": 2131, "human": 187, "generic": 78}

# Split on sentence punctuation after
# flattening newlines, and strip a leading bullet or number before comparing.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
BULLET = re.compile(r"^[\s\-\*•\d\.\)]+")


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text.replace("\n", " "))
    return [s.strip() for s in SENTENCE_END.split(flat) if s.strip()]


def normalize(s: str) -> str:
    return BULLET.sub("", s).lower().strip()


def levels(run: dict, with_names: bool = False):
    out = []
    for p in (DATA / run["path"] / "levels").iterdir():
        if p.is_dir() and p.name[1:].isdigit() and (p / "system_prompt.md").exists():
            out.append((int(p.name[1:]),
                        (p / "system_prompt.md").read_text(encoding="utf-8", errors="replace")))
    out.sort()
    return [(f"L{n}", t) for n, t in out] if with_names else [t for _, t in out]


def collect() -> list[dict]:
    """Every distinct referent sentence, deduplicated within its run."""
    manifest, lexicons, corpora = load("MANIFEST.json"), load("lexicons.json"), load("corpora.json")
    patterns = {
        fid.split(".", 1)[1]: re.compile(
            "|".join(word_pattern(s) for s in lexicons["families"][fid]["stems"]), re.I)
        for fid in lexicons["sets"][REPORTED_SET]["families"]
    }
    sel = corpora["corpora"][REPORTED_CORPUS]["selector"]
    out = []
    for r in [r for r in manifest["runs"] if r["mode"] in sel["modes"]]:
        seen = set()
        for lvl, text in levels(r, with_names=True):
            for s in sentences(text):
                for ref, rx in patterns.items():
                    if not rx.search(s):
                        continue
                    key = (ref, normalize(s))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({"referent": ref, "run": r["id"], "mode": r["mode"],
                                "display_name": r["display_name"], "level": lvl,
                                "sentence": s})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--by-model", action="store_true")
    args = ap.parse_args()

    manifest, lexicons, corpora = load("MANIFEST.json"), load("lexicons.json"), load("corpora.json")
    spec = lexicons["sets"][REPORTED_SET]
    patterns = {
        fid.split(".", 1)[1]: re.compile(
            "|".join(word_pattern(s) for s in lexicons["families"][fid]["stems"]), re.I)
        for fid in spec["families"]
    }
    sel = corpora["corpora"][REPORTED_CORPUS]["selector"]
    runs = [r for r in manifest["runs"] if r["mode"] in sel["modes"]]

    print(f"corpus     {REPORTED_CORPUS} ({len(runs)} runs, every committed level)")
    print(f"vocabulary {REPORTED_SET}")
    print("unit       distinct sentence, deduplicated within a run\n")

    dedup, raw = Counter(), Counter()
    by_model = {ref: Counter() for ref in patterns}
    for r in runs:
        seen = set()
        for text in levels(r):
            for s in sentences(text):
                for ref, rx in patterns.items():
                    if not rx.search(s):
                        continue
                    raw[ref] += 1
                    key = (ref, normalize(s))
                    if key in seen:
                        continue
                    seen.add(key)
                    dedup[ref] += 1
                    by_model[ref][r["display_name"]] += 1

    for ref in ("user", "human", "generic"):
        line = f"  {ref:<9} {dedup[ref]:>5}"
        if args.raw:
            line += f"   (raw {raw[ref]})"
        print(f"{line}   published {PUBLISHED[ref]}")

    print(f"\n  user names the addressee {dedup['user']/dedup['human']:.1f}x more often "
          f"than human — §4.6 says an order of magnitude")

    if args.by_model:
        names = [m["display_name"] for m in
                 sorted({r["api_model"]: r for r in runs}.values(), key=lambda r: r["api_model"])]
        print(f"\n  {'model':<20} " + "  ".join(f"{r:>8}" for r in patterns))
        for n in names:
            print(f"  {n:<20} " + "  ".join(f"{by_model[ref][n]:>8}" for ref in patterns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
