#!/usr/bin/env python3
"""Theme presence rates over a declared corpus, lexicon and aggregation.

Every input is named rather than inlined: the corpus comes from corpora.json, the
keyword family from lexicons.json, the within-run weighting from the aggregations
block of corpora.json. Nothing here hardcodes which runs, which stems or which
weighting to use, because getting any of those wrong silently is how §4.3.1 came
to report 45/49/80 over the wrong corpus with the wrong weighting.

Produces the §4.3.1 numbers.

    python3 repro/themes.py                                  # the reported table
    python3 repro/themes.py --aggregation prompt             # compare weightings
    python3 repro/themes.py --lexicon curiosity.v1 --show-hits
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

# The three themes §4.3.1 reports, each naming a family in lexicons.json.
REPORTED = {
    "honesty": "honesty.v1",
    "curiosity": "curiosity.v1",
    "helpfulness": "helpfulness.v1",
}
REPORTED_CORPUS = "freedom-18"
REPORTED_AGGREGATION = "run_mean_fraction"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


from _corpus import select_runs


def run_texts(run: dict) -> list[str]:
    """Self-authored prompts of one run, in level order."""
    lv = sorted(
        (p for p in (DATA / run["path"] / "levels").iterdir()
         if p.is_dir() and p.name != "L0" and p.name[1:].isdigit()),
        key=lambda p: int(p.name[1:]),
    )
    return [(p / "system_prompt.md").read_text(encoding="utf-8", errors="replace").lower()
            for p in lv if (p / "system_prompt.md").exists()]


def word_pattern(stem: str) -> str:
    """A stem under match=word. A trailing '*' means word-start prefix:
    'communit*' matches community and communities, but not subcommunity."""
    if stem.endswith("*"):
        return rf"\b{re.escape(stem[:-1])}\w*"
    return rf"\b{re.escape(stem)}\b"


def matches(text: str, family: dict) -> bool:
    if family.get("match") == "word":
        return any(re.search(word_pattern(s), text) for s in family["stems"])
    excl = family.get("exclude_forms", ())
    if excl:
        # A stem hit only counts if some matching word form survives the
        # exclusions: "harm" is a hit in "harmful" but not in "harmonize".
        return any(
            m.group(0) for s in family["stems"]
            for m in re.finditer(rf"\w*{re.escape(s)}\w*", text)
            if not any(x in m.group(0) for x in excl)
        )
    return any(s in text for s in family["stems"])


def rate(runs: list[dict], family: dict, aggregation: str) -> tuple[float, int, str]:
    """Returns (percentage, n observations, unit label)."""
    if aggregation == "prompt":
        texts = [t for r in runs for t in run_texts(r)]
        return 100 * sum(matches(t, family) for t in texts) / len(texts), len(texts), "prompts"
    if aggregation == "run_final":
        finals = [run_texts(r)[-1] for r in runs if run_texts(r)]
        return 100 * sum(matches(t, family) for t in finals) / len(finals), len(finals), "runs"
    if aggregation == "run_mean_fraction":
        per_run = [mean(matches(t, family) for t in run_texts(r)) for r in runs if run_texts(r)]
        return 100 * mean(per_run), len(per_run), "runs"
    raise SystemExit(f"unknown aggregation {aggregation!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=REPORTED_CORPUS)
    ap.add_argument("--aggregation", default=REPORTED_AGGREGATION)
    ap.add_argument("--lexicon", action="append",
                    help="family id; repeatable. Default: the three §4.3.1 themes.")
    ap.add_argument("--show-hits", action="store_true",
                    help="list per-run values instead of only the summary")
    args = ap.parse_args()

    manifest, corpora, lexicons = load("MANIFEST.json"), load("corpora.json"), load("lexicons.json")

    if args.aggregation not in corpora["aggregations"]:
        raise SystemExit(f"unknown aggregation {args.aggregation!r}")
    agg_spec = corpora["aggregations"][args.aggregation]

    fams = {f: f for f in args.lexicon} if args.lexicon else REPORTED
    for fid in fams.values():
        if fid not in lexicons["families"]:
            raise SystemExit(f"unknown lexicon {fid!r}")

    runs = select_runs(manifest, corpora, args.corpus)

    print(f"corpus      {args.corpus}  ({len(runs)} runs)")
    print(f"aggregation {args.aggregation} — {agg_spec['description']}")
    if args.aggregation != REPORTED_AGGREGATION:
        print(f"            NOTE: §4.3.1 reports {REPORTED_AGGREGATION} (decision A1a)")
    print()

    for theme, fid in fams.items():
        fam = lexicons["families"][fid]
        pct, n, unit = rate(runs, fam, args.aggregation)
        print(f"  {theme:<13} {pct:>5.1f}%   n={n} {unit:<8} [{fid}]")
        if args.show_hits and args.aggregation == "run_mean_fraction":
            for r in sorted(runs, key=lambda x: (x["api_model"], x["run"])):
                ts = run_texts(r)
                if ts:
                    print(f"      {100*mean(matches(t, fam) for t in ts):>5.0f}%  "
                          f"{r['api_model']}/run{r['run']}  ({len(ts)} levels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
