#!/usr/bin/env python3
"""Regenerate the §G dimensional coding (Table 8). Tier B: paid.

One call per authored level, so the input set is exactly the 690 non-L0
system prompts in data/. inputs.jsonl carries a pointer and a sha1 rather
than the prompt text; verify-inputs re-derives the level set from
MANIFEST.json and re-hashes every file, so a changed prompt fails.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "dimensional"


def authored_levels() -> dict[tuple[str, str], Path]:
    """Every non-L0 level with a system prompt, keyed by (run id, level)."""
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    out = {}
    for r in manifest["runs"]:
        for p in (DATA / r["path"] / "levels").iterdir():
            f = p / "system_prompt.md"
            if p.is_dir() and p.name != "L0" and p.name[1:].isdigit() and f.exists():
                out[(r["id"], p.name)] = f
    return out


def verify_inputs() -> tuple[bool, str]:
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    frozen = [json.loads(l) for l in
              (FROZEN / "inputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    outputs = [json.loads(l) for l in
               (FROZEN / "outputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    if len(frozen) != meta["n_items"]:
        return False, f"{len(frozen)} input records, meta says {meta['n_items']}"
    if [r["id"] for r in outputs] != [r["id"] for r in frozen]:
        return False, f"{len(outputs)} outputs do not align with {len(frozen)} inputs"

    mine = authored_levels()
    froz = {(r["run"], r["level"]): r for r in frozen}
    if len(froz) != len(frozen):
        return False, "inputs.jsonl repeats a (run, level)"
    missing, extra = set(mine) - set(froz), set(froz) - set(mine)
    if missing or extra:
        return False, (f"{len(missing)} authored levels absent from the artifact, "
                       f"{len(extra)} artifact rows with no level in data/")

    for key, f in mine.items():
        text = f.read_text(encoding="utf-8", errors="replace")
        got = hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()
        if got != froz[key]["sha1"]:
            return False, f"{key[0]}/{key[1]} changed since coding ({got[:12]})"

    by_mode = {}
    for r in frozen:
        by_mode[r["mode"]] = by_mode.get(r["mode"], 0) + 1
    if by_mode != meta["by_mode"]:
        return False, f"per-mode split {by_mode} does not match meta {meta['by_mode']}"

    return True, (f"{len(froz)} authored levels re-derived from data/ and re-hashed, "
                  f"{by_mode}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-inputs", action="store_true")
    args = ap.parse_args()
    if args.verify_inputs:
        ok, msg = verify_inputs()
        print(f"verify-inputs: {'OK' if ok else 'FAILED'}, {msg}")
        return 0 if ok else 1
    print("regeneration is not wired up yet; --verify-inputs is the Tier A half")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
