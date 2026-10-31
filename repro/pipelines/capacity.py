#!/usr/bin/env python3
"""Regenerate the §4.6 capacity coding (Figure 8). Tier B: paid.

The coding ran on a slightly different sentence split from the one
repro/referents.py uses now, so the re-derived input set does not match the
frozen one exactly. That delta is pinned by hash in meta.json: the known 42
differences pass, anything else fails.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import referents

FROZEN = Path(__file__).resolve().parents[2] / "frozen" / "capacity"


def _norm(s: str) -> str:
    return " ".join(s.split())


def verify_inputs() -> tuple[bool, str]:
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    prov = meta["input_provenance"]
    frozen = [json.loads(l) for l in
              (FROZEN / "inputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    froz = {(r["referent"], _norm(r["sentence"])) for r in frozen}
    mine = {(r["referent"], _norm(r["sentence"])) for r in referents.collect()}
    blob = json.dumps({"frozen_only": sorted(froz - mine),
                       "rederived_only": sorted(mine - froz)},
                      ensure_ascii=False, sort_keys=True)
    got = hashlib.sha256(blob.encode()).hexdigest()

    if len(frozen) != meta["n_items"]:
        return False, f"{len(frozen)} input records, meta says {meta['n_items']}"
    if got != prov["known_delta_sha256"]:
        return False, (f"input delta changed: {len(froz - mine)} frozen-only, "
                       f"{len(mine - froz)} re-derived-only, sha {got[:12]} "
                       f"not {prov['known_delta_sha256'][:12]}")
    return True, (f"{len(froz & mine)} of {len(froz)} sentences re-derived from data/, "
                  f"{prov['known_delta_n']} known-delta")


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
