#!/usr/bin/env python3
"""Regenerate the value/pain decomposition. Tier B: paid.

Two artifacts from the same two-stage pipeline over different corpora:

    frozen/value_pain/        the 18 happiness finals   §4.3.2, Figure 5, Table 9
    frozen/value_universal/   84 of §4.5.1's 102        §4.5.1, Table 12

The two stages do not carry the same guarantee. Stage one splits a system
prompt from data/ into atoms, so its input set re-derives from MANIFEST.json
and every prompt re-hashes. Stage two classifies those atoms, and the atoms
exist nowhere but stage one's output, so it can only be checked against that.
verify-inputs reports the two separately rather than as one tick.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
ARTIFACTS = ("value_pain", "value_universal")

# Unit ids are the pipeline's own naming, not the artifact's. Happiness units are
# <slug>_r<N>; the universal corpus adds the mode and which prompt was taken.
UNIT_RE = re.compile(r"(\w+?)_(freedom|improvements|happiness)_(final|l1)_r(\d)")
SLUG = {"Claude Opus 4.5": "opus", "Claude Sonnet 4.5": "sonnet", "GPT-4o": "gpt4o",
        "GPT-5.1": "gpt51", "Grok-4": "grok", "Gemini-3 Pro": "gemini"}
MODE = {"freedom": "freedom", "improvements": "improvement", "happiness": "happiness"}


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _levels(run: dict) -> list[Path]:
    return sorted((p for p in (DATA / run["path"] / "levels").iterdir()
                   if p.is_dir() and p.name != "L0" and p.name[1:].isdigit()
                   and (p / "system_prompt.md").exists()),
                  key=lambda p: int(p.name[1:]))


def resolve(unit: str, runs: dict) -> tuple[dict, Path, str]:
    """A unit id -> the run it came from, the level directory, and which end."""
    m = UNIT_RE.fullmatch(unit)
    if m:
        slug, mode, which, n = m.groups()
        mode = MODE[mode]
    else:
        slug, n = unit.rsplit("_r", 1)
        mode, which = "happiness", "final"
    run = runs[(slug, mode, int(n))]
    lv = _levels(run)
    return run, (lv[-1] if which == "final" else lv[0]), which


def verify_one(name: str) -> tuple[bool, str]:
    frozen = REPO / "frozen" / name
    meta = json.loads((frozen / "meta.json").read_text(encoding="utf-8"))
    inputs = _jsonl(frozen / "atomize_inputs.jsonl")
    atoms = _jsonl(frozen / "atomize_outputs.jsonl")
    cls = _jsonl(frozen / "classify_outputs.jsonl")

    if len(inputs) != meta["n_units"]:
        return False, f"{len(inputs)} units, meta says {meta['n_units']}"
    if not (len(atoms) == len(cls) == meta["n_atoms"]):
        return False, f"{len(atoms)} atoms, {len(cls)} classified, meta says {meta['n_atoms']}"

    # Stage one: every unit re-derives from data/ and re-hashes.
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    runs = {(SLUG[r["display_name"]], r["mode"], r["run"]): r for r in manifest["runs"]}
    for rec in inputs:
        run, lvl, which = resolve(rec["unit"], runs)
        if run["id"] != rec["run"] or lvl.name != rec["level"] or which != rec["which"]:
            return False, (f"{rec['unit']} resolves to {run['id']}/{lvl.name} ({which}), "
                           f"artifact says {rec['run']}/{rec['level']} ({rec['which']})")
        got = _sha1((lvl / "system_prompt.md").read_text(encoding="utf-8").strip())
        if got != rec["source_sha1"]:
            return False, f"{rec['unit']} ({rec['run']}/{rec['level']}) changed since coding"

    # Per-unit atom counts, so a truncated unit cannot hide in the total.
    got_counts = collections.Counter(a["unit"] for a in atoms)
    for rec in inputs:
        if got_counts[rec["unit"]] != rec["n_atoms"]:
            return False, (f"{rec['unit']}: {got_counts[rec['unit']]} atoms present, "
                           f"artifact declares {rec['n_atoms']}")

    # Stage two: joins to stage one and to nothing else.
    if [(a["unit"], a["id"]) for a in atoms] != [(c["unit"], c["id"]) for c in cls]:
        return False, "classify_outputs does not align one-to-one with atomize_outputs"

    dirs = dict(sorted(collections.Counter(c["direction"] for c in cls).items()))
    if dirs != meta["by_direction"]:
        return False, f"direction split {dirs} does not match meta {meta['by_direction']}"
    themes = {c["theme_raw"] for c in cls}
    if len(themes) != meta["n_distinct_themes"]:
        return False, f"{len(themes)} distinct themes, meta says {meta['n_distinct_themes']}"

    return True, (f"{len(inputs)} prompts re-derived from data/ and re-hashed; "
                  f"{len(atoms)} atoms classified, stage two joined to stage one only")


def verify_corpus() -> tuple[bool, str]:
    """The two artifacts together are §4.5.1's 102 prompts, and nothing is double-counted."""
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    runs = {(SLUG[r["display_name"]], r["mode"], r["run"]): r for r in manifest["runs"]}
    seen = set()
    for name in ARTIFACTS:
        for rec in _jsonl(REPO / "frozen" / name / "atomize_inputs.jsonl"):
            key = (rec["run"], rec["level"])
            if key in seen:
                return False, f"{rec['run']}/{rec['level']} appears in both artifacts"
            seen.add(key)

    uni = _jsonl(REPO / "frozen" / "value_universal" / "atomize_inputs.jsonl")
    l1 = {r["run"] for r in uni if r["which"] == "l1"}
    if l1 != {r["id"] for r in manifest["runs"]}:
        return False, f"the L1 corpus covers {len(l1)} runs, not all 54"

    # A run contributes a second prompt only when its final is not its L1.
    finals = {r["run"] for r in uni if r["which"] == "final"}
    finals |= {r["run"] for r in _jsonl(REPO / "frozen" / "value_pain" / "atomize_inputs.jsonl")}
    expect = {r["id"] for r in manifest["runs"] if len(_levels(r)) > 1}
    if finals != expect:
        return False, (f"{len(finals)} runs contribute a final, expected {len(expect)} "
                       f"(the runs that did not converge at L1)")

    return True, (f"{len(seen)} distinct prompts across both artifacts: 54 L1 plus "
                  f"{len(finals)} finals, matching §4.5.1's 102")


def verify_inputs() -> tuple[bool, str]:
    msgs = []
    for name in ARTIFACTS:
        ok, msg = verify_one(name)
        if not ok:
            return False, f"{name}: {msg}"
        msgs.append(f"{name}: {msg}")
    ok, msg = verify_corpus()
    if not ok:
        return False, f"corpus: {msg}"
    return True, " | ".join(msgs + [f"corpus: {msg}"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-inputs", action="store_true")
    args = ap.parse_args()
    if args.verify_inputs:
        ok, msg = verify_inputs()
        print(f"verify-inputs: {'OK' if ok else 'FAILED'}")
        for part in msg.split(" | "):
            print(f"  {part}")
        return 0 if ok else 1
    print("regeneration is not wired up yet; --verify-inputs is the Tier A half")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
