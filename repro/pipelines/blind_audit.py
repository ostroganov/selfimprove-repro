#!/usr/bin/env python3
"""Regenerate the §4.3.3 blind audit (Table 10). Tier B: paid, non-deterministic.

repro/blind_audit.py counts the frozen verdicts; this reproduces them.

Runs come from MANIFEST.json through _corpus, never from directory names. The
frozen artifact was produced by two invocations with separate RNG streams, so
--verify-inputs takes the same list of captures; see frozen/blind_audit/meta.json.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _corpus

FROZEN = Path(__file__).resolve().parents[2] / "frozen" / "blind_audit"

SLUGS = {"opus": "claude-opus-4-5-20251101", "sonnet": "claude-sonnet-4-5-20250929",
         "gpt4o": "gpt-4o", "gpt51": "gpt-5.1", "grok": "grok-4-0709",
         "gemini": "gemini-3-pro-preview"}

# Questions leaking the level identity or the experiment framing would confound
# a blind judge; short ones cannot discriminate.
_META_Q = re.compile(
    r"system prompt|self-improvement experiment|\bcandidate\b|draft v\d|"
    r"\byou are l\d|under the latest draft|\btest [a-e]\b|meta-?test", re.IGNORECASE)


def clean_question(q: str):
    q = (q or "").strip()
    if not q or len(q) < 12 or _META_Q.search(q):
        return None
    return re.sub(r'^\s*User:\s*"?', "", q).strip() or None


def pick_questions(transition, rng, k):
    convs = _corpus.conversations(transition)
    rng.shuffle(convs)
    out = []
    for c in convs:
        try:
            d = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        q = clean_question(d.get("initial_prompt"))
        if q:
            out.append((q, (d.get("metadata") or {}).get("context", ""), c.name))
        if len(out) >= k:
            break
    return out


def spread(items, k):
    if k >= len(items):
        return items
    idx = [round(i * (len(items) - 1) / (k - 1)) for i in range(k)] if k > 1 else [0]
    seen, out = set(), []
    for i in idx:
        while i in seen:
            i += 1
        if i < len(items):
            seen.add(i)
            out.append(items[i])
    return out


def sample(slugs, per_model, rng, min_n=0, q_per=1, manifest=None):
    manifest = manifest or _corpus.load()[0]
    rows = []
    for slug in slugs:
        api_model = SLUGS[slug]
        runs = sorted((r for r in manifest["runs"]
                       if r["mode"] == "improvement" and r["api_model"] == api_model),
                      key=lambda r: r["run"])
        pool = []
        for run in runs:
            for t in _corpus.committed_transitions(run):
                if t["n"] < min_n:
                    continue
                for (q, ctx, conv) in pick_questions(t, rng, q_per):
                    pool.append(dict(model=slug, api_model=api_model, run=run["id"],
                                     n=t["n"], np1=t["np1"], transition=t["name"],
                                     conv=conv, question=q, context=ctx,
                                     parent_prompt=t["parent_prompt"],
                                     successor_prompt=t["successor_prompt"]))
        rows.extend(spread(pool, per_model))
    return rows


def verify_inputs() -> tuple[bool, str]:
    """Re-derive the frozen selection. Generated answers are outputs, not inputs."""
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    s = meta["sampling"]
    manifest = _corpus.load()[0]
    got = []
    for inv in s["invocations"]:
        got += sample(inv["models"], s["per_model"], random.Random(s["seed"]),
                      s["min_n"], s["q_per_transition"], manifest)
    frozen = [json.loads(l) for l in (FROZEN / "inputs.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]

    key = lambda m, r, t, q: (m, r.split("run")[-1], t, q.strip())
    a = {key(r["api_model"], r["run"], r["transition"], r["question"]) for r in got}
    b = {key(r["api_model"], r["run"], r["transition"], r["question"]) for r in frozen}
    if a == b:
        return True, f"{len(a)} comparisons re-derived from data/"
    only_f, only_a = sorted(b - a), sorted(a - b)
    return False, (f"re-derived {len(a)} vs frozen {len(b)}; "
                   f"{len(only_f)} only in frozen, {len(only_a)} only re-derived"
                   + (f"; first missing {only_f[0]}" if only_f else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-inputs", action="store_true",
                    help="re-derive the frozen selection and compare (free, offline)")
    args = ap.parse_args()
    if args.verify_inputs:
        ok, msg = verify_inputs()
        print(f"verify-inputs: {'OK' if ok else 'FAILED'}, {msg}")
        return 0 if ok else 1
    print("regeneration is not wired up yet; --verify-inputs is the Tier A half")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
