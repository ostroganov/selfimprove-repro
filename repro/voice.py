#!/usr/bin/env python3
"""§H voice analysis: how each final prompt addresses its subject. Tier A.

Voice is pronoun dominance over the final committed prompt: *second* when
second-person pronouns outnumber first-person ("You are..."), *first* when they
are outnumbered, *other* on a tie, which includes a prompt using neither.

Produces the Voice row of Table 8 and the Voice column of Table 13.

The AI-identity column of Table 13 is not produced here. Those labels were read
from the prompts by the authors and no rule generates them, so the artifact
reports them as read rather than inventing a rule that would reproduce them by
construction. Table 13's other two columns are recomputed.

    python3 repro/voice.py
    python3 repro/voice.py --all          # every run, not just happiness
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

MODES = ["freedom", "improvement", "happiness"]
ORDER = ["second", "first", "other"]

YOU_RE = re.compile(r"\b(you|your|you're|yours|yourself)\b", re.I)
I_RE = re.compile(r"\b(i|i'm|my|me|mine|myself|i've|i'll|i'd)\b", re.I)


def classify(text: str) -> tuple[str, int, int]:
    you, i = len(YOU_RE.findall(text)), len(I_RE.findall(text))
    if you == i:                      # covers the both-zero case
        return "other", you, i
    return ("second" if you > i else "first"), you, i


def final_prompt(run: dict) -> tuple[str, str]:
    levels = sorted((p for p in (DATA / run["path"] / "levels").iterdir()
                     if p.is_dir() and p.name != "L0" and p.name[1:].isdigit()
                     and (p / "system_prompt.md").exists()),
                    key=lambda p: int(p.name[1:]))
    top = levels[-1]
    return (top / "system_prompt.md").read_text(encoding="utf-8").strip(), top.name


def opening(text: str, n: int = 80) -> str:
    line = text.splitlines()[0] if text.strip() else ""
    return (line[:n] + "…") if len(line) > n else line


def rows() -> list[dict]:
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    out = []
    for r in manifest["runs"]:
        text, level = final_prompt(r)
        v, you, i = classify(text)
        out.append({"run": r["id"], "mode": r["mode"], "display_name": r["display_name"],
                    "n": r["run"], "level": level, "voice": v, "you": you, "i": i,
                    "words": len(text.split()), "opening": opening(text)})
    return out


def by_mode() -> dict:
    """mode -> {voice: runs}, the Voice row of Table 8."""
    out = defaultdict(Counter)
    for r in rows():
        out[r["mode"]][r["voice"]] += 1
    return {m: dict(out[m]) for m in MODES}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="every run, not just happiness")
    args = ap.parse_args()

    all_rows = rows()
    print("unit       the final committed prompt of each run")
    print("rule       pronoun dominance; a tie is 'other'\n")
    counts = by_mode()
    print(f"  {'mode':<14} " + "  ".join(f"{v:>7}" for v in ORDER) + "     Table 8's Voice row")
    for m in MODES:
        c = counts[m]
        cells = "  ".join(f"{c.get(v, 0):>7}" for v in ORDER)
        printed = ", ".join(f"{v} {c[v]}" for v in ORDER if c.get(v))
        print(f"  {m:<14} {cells}     {printed}")

    shown = all_rows if args.all else [r for r in all_rows if r["mode"] == "happiness"]
    print(f"\n  {'model':<20} {'run':>3} {'level':>6} {'voice':>7} {'you':>5} {'I':>5}   opening")
    for r in sorted(shown, key=lambda r: (r["display_name"], r["n"])):
        print(f"  {r['display_name']:<20} {r['n']:>3} {r['level']:>6} {r['voice']:>7} "
              f"{r['you']:>5} {r['i']:>5}   {r['opening'][:52]}")
    if not args.all:
        print("\n  Table 13's AI-identity column is author-read and is not recomputed here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
