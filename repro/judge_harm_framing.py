#!/usr/bin/env python3
"""Tier B: the harm-framing judge pass. Costs money; opt-in.

Cross-checks the manual review behind §4.3.1's claim that harm vocabulary in the
freedom corpus appears only in refusal or avoidance framing. The judge is
prompted adversarially — asked to build the case that a passage *advances* harm —
so agreement is not the path of least resistance. See frozen/harm_framing/labels.json.

The prompt is not in this file. It is parsed out of frozen/harm_framing/prompt.md,
so what ran and what is published cannot drift apart.

Every occurrence in inputs.jsonl gets its own call, repeats included: identical
text judged differently is a fact about the judge worth recording.

Requires `anthropic` and ANTHROPIC_API_KEY. Not part of Tier A — nothing in
check.py imports this.

    python3 repro/judge_harm_framing.py --dry-run     # show prompts, call nothing
    python3 repro/judge_harm_framing.py               # ~27 calls, cents
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MODEL = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.0
MAX_TOKENS = 600
RETRIES = 8          # 500s from the API arrive in clusters; ride them out
MAX_BACKOFF = 60
# USD per million tokens, for the cost record in meta.json.
PRICE_IN, PRICE_OUT = 1.00, 5.00


def parse_prompt(md: str) -> tuple[str, str]:
    """(system prompt, user template) from prompt.md's two ## sections."""
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*$(.*?)(?=^## |\Z)", md,
                      re.M | re.S)
        if not m:
            raise SystemExit(f"prompt.md has no '## {name}' section")
        return m.group(1).strip()

    system = section("System prompt")
    fences = re.findall(r"```(?:\w+)?\n(.*?)```", section("Input"), re.S)
    if not fences:
        raise SystemExit("prompt.md '## Input' section has no fenced template")
    # Deliberately NOT stripped: the fenced block in prompt.md ends with a
    # newline, so that newline is part of what gets sent. Keeping the template
    # literal is the point — prompt.md is meant to be what went over the wire.
    template = fences[0]
    if "<text>" not in template:
        raise SystemExit("prompt.md input template lacks a <text> placeholder")
    return system, template


def extract_json(text: str) -> dict:
    """The judge is asked for bare JSON; tolerate a fenced or padded reply."""
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
    if fence:
        t = fence.group(1)
    else:
        start, end = t.find("{"), t.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON object in reply: {text[:200]!r}")
        t = t[start:end + 1]
    return json.loads(t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="frozen/harm_framing")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the first rendered call and exit without spending")
    ap.add_argument("--limit", type=int, help="judge only the first N occurrences")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore existing outputs and re-judge everything")
    ap.add_argument("--controls", action="store_true",
                    help="judge the synthetic controls instead of the corpus")
    args = ap.parse_args()

    d = REPO / args.dir
    if args.controls:
        # Synthetic passages, never mixed with the corpus. See controls.json.
        inputs = [{"id": ctl["id"], "sha": ctl["id"], "context": ctl["context"],
                   "expect": ctl["expect"], "scored": ctl["scored"]}
                  for ctl in json.loads(
                      (d / "controls.json").read_text(encoding="utf-8"))["controls"]]
    else:
        inputs = [json.loads(ln) for ln in
                  (d / "inputs.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.limit:
        inputs = inputs[:args.limit]

    name = "controls_outputs.jsonl" if args.controls else "outputs.jsonl"
    done = {}
    if (d / name).exists() and not args.fresh:
        for ln in (d / name).read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                done[r["id"]] = r
        if done:
            print(f"resuming: {len(done)} of {len(inputs)} already judged "
                  f"(--fresh to redo all)")
    prompt_md = (d / "prompt.md").read_text(encoding="utf-8")
    system, template = parse_prompt(prompt_md)
    allowed = json.loads((d / "labels.json").read_text(encoding="utf-8"))

    if args.dry_run:
        print(f"model {MODEL}  temperature {TEMPERATURE}  calls {len(inputs)}")
        print(f"\n--- system prompt ({len(system)} chars) ---\n{system}")
        print(f"\n--- first user message ---\n{template.replace('<text>', inputs[0]['context'])}")
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    import anthropic
    client = anthropic.Anthropic()

    results, tok_in, tok_out = [], 0, 0

    def flush():
        """Write after every call: a later failure must not discard paid work."""
        (d / name).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
            encoding="utf-8")

    for n, rec in enumerate(inputs, 1):
        if rec["id"] in done:
            results.append(done[rec["id"]])
            continue
        msg = template.replace("<text>", rec["context"])
        # Overload (529), rate limits and connection drops are worth waiting out;
        # anything else (auth, bad request) is a bug and should surface now.
        transient = (anthropic.APIConnectionError, anthropic.RateLimitError,
                     anthropic.InternalServerError)
        for attempt in range(RETRIES):
            try:
                resp = client.messages.create(
                    model=MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
                    system=system, messages=[{"role": "user", "content": msg}])
                break
            except transient as e:
                if attempt == RETRIES - 1:
                    raise
                wait = min(2 ** attempt, MAX_BACKOFF)
                print(f"  {rec['id']}: {type(e).__name__}, retry in {wait}s", flush=True)
                time.sleep(wait)

        tok_in += resp.usage.input_tokens
        tok_out += resp.usage.output_tokens
        raw = "".join(b.text for b in resp.content if b.type == "text")
        try:
            v = extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  [{n}/{len(inputs)}] {rec['id']}  UNPARSEABLE: {e}", file=sys.stderr)
            v = {"verdict": "unclear", "label": "other",
                 "adversarial_case": "", "note": f"unparseable reply: {raw[:300]}"}

        out = {
            "sha": rec["sha"], "id": rec["id"],
            "verdict": v.get("verdict"), "label": v.get("label"),
            "adversarial_case": v.get("adversarial_case", ""),
            "note": v.get("note", ""),
        }
        bad = []
        if out["verdict"] not in allowed["verdicts"]:
            bad.append(f"verdict {out['verdict']!r}")
        if out["label"] not in allowed["labels"]:
            bad.append(f"label {out['label']!r}")
        if args.controls:
            out["expect"], out["scored"] = rec["expect"], rec["scored"]
            hit = out["verdict"] == rec["expect"]
            bad.append("MISS") if rec["scored"] and not hit else None
        results.append(out)
        flush()
        flag = "  " + ", ".join(bad) if bad else ""
        if args.controls:
            mark = "ok " if out["verdict"] == rec["expect"] else "MISS"
            print(f"  [{n}/{len(inputs)}] {rec['id']:<34} {out['verdict']:<12} "
                  f"expect {rec['expect']:<12} {mark}{'' if rec['scored'] else ' (unscored)'}")
        else:
            print(f"  [{n}/{len(inputs)}] {rec['id']:<34} {out['verdict']:<12} {out['label']}{flag}")

    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    (d / ("controls_meta.json" if args.controls else "meta.json")).write_text(json.dumps({
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_calls": len(results),
        "n_distinct_contexts": len({r["sha"] for r in results}),
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "usd": round(cost, 4),
        "prompt_sha256": hashlib.sha256(prompt_md.encode()).hexdigest()[:16],
        "note": ("Temperature 0 is not determinism: a re-run may differ. These "
                 "outputs are the primary record of what the judge said."),
    }, indent=2) + "\n", encoding="utf-8")

    # Same text, different label, is a fact about the judge, not the data.
    by_sha: dict[str, set] = {}
    for r in results:
        by_sha.setdefault(r["sha"], set()).add((r["verdict"], r["label"]))
        inconsistent = {k: v for k, v in by_sha.items() if len(v) > 1}

    print(f"\nverdicts  {json.dumps({v: sum(1 for r in results if r['verdict'] == v) for v in allowed['verdicts']})}")
    print(f"labels    {json.dumps({l: sum(1 for r in results if r['label'] == l) for l in allowed['labels'] if any(r['label'] == l for r in results)})}")
    print(f"tokens    {tok_in} in, {tok_out} out — ${cost:.4f}")
    if args.controls:
        scored = [r for r in results if r["scored"]]
        miss = [r["id"] for r in scored if r["verdict"] != r["expect"]]
        print(f"controls  {len(scored) - len(miss)}/{len(scored)} scored controls correct"
              + (f"; MISSED {miss}" if miss else ""))
        print(f"wrote     {args.dir}/controls_outputs.jsonl, {args.dir}/controls_meta.json")
        return 1 if miss else 0
    print(f"identical text judged differently: {len(inconsistent)} of {len(by_sha)} contexts"
          + (f" {list(inconsistent)}" if inconsistent else ""))
    print(f"wrote     {args.dir}/outputs.jsonl, {args.dir}/meta.json")
    print(f"          re-run `make contexts` to fold labels into contexts.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
