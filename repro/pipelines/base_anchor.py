#!/usr/bin/env python3
"""Regenerate §I's base-model anchor elicitation. Tier B: paid.

Each bare model, with no system prompt, is asked three questions about its own
values, twice each. §I compares those answers to the model's self-improvement
endpoints, testing whether a model's stated values pre-exist the loop.

This is the one frozen artifact whose inputs are not derived from data/: they
are a fixed prompt list. There is nothing to re-derive, so verify-inputs checks
the shape rather than the provenance — the prompts are the ones in prompt.md,
the models are MANIFEST models, and the record is models x prompts x samples
with no gaps. That is a weaker guarantee than the other pipelines carry, and
meta.json says so rather than implying otherwise.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "base_anchor"


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def prompts() -> list[str]:
    """The elicitation prompts, parsed out of prompt.md rather than duplicated here."""
    out = []
    for line in (FROZEN / "prompt.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line[:1].isdigit() and ". " in line:
            out.append(line.split(". ", 1)[1])
    return out


def verify_inputs() -> tuple[bool, str]:
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    inputs, outputs = _jsonl(FROZEN / "inputs.jsonl"), _jsonl(FROZEN / "outputs.jsonl")
    ps = prompts()

    if len(inputs) != meta["n_items"]:
        return False, f"{len(inputs)} inputs, meta says {meta['n_items']}"
    if [r["id"] for r in outputs] != [r["id"] for r in inputs]:
        return False, "outputs do not align one-to-one with inputs"
    if len(ps) != meta["n_prompts"]:
        return False, f"prompt.md carries {len(ps)} prompts, meta says {meta['n_prompts']}"

    expect = len(meta["models"]) * meta["n_prompts"] * meta["samples_per_prompt"]
    if len(inputs) != expect:
        return False, (f"{len(inputs)} elicitations, expected "
                       f"{len(meta['models'])} models x {meta['n_prompts']} prompts "
                       f"x {meta['samples_per_prompt']} samples = {expect}")

    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    known = set(manifest["models"])
    for slug, mid in meta["models"].items():
        if mid not in known:
            return False, f"{slug} elicits {mid}, which is not a model in MANIFEST.json"

    # Every (model, prompt, sample) cell filled exactly once, and each input
    # carrying the prompt text its index names.
    cells = Counter((r["model"], r["prompt_index"], r["sample"]) for r in inputs)
    if set(cells.values()) != {1}:
        dupes = [k for k, v in cells.items() if v != 1]
        return False, f"{len(dupes)} (model, prompt, sample) cells are not filled exactly once"
    for r in inputs:
        if r["prompt"] != ps[r["prompt_index"]]:
            return False, f"input {r['id']} carries text that is not prompt {r['prompt_index']}"
    if any(not o["text"].strip() for o in outputs):
        return False, "an elicitation came back empty"

    excluded = ", ".join(meta.get("excluded", {}))
    return True, (f"{len(inputs)} elicitations over {len(meta['models'])} models "
                  f"x {len(ps)} prompts x {meta['samples_per_prompt']} samples"
                  + (f"; {excluded} has no base model" if excluded else ""))


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
