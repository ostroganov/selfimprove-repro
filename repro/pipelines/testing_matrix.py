#!/usr/bin/env python3
"""Code what each test question asked. Tier B: paid.

Table 3's five content rows: the four question-content categories, coded from
the first user turn of every improvement-mode evaluation conversation, and
adversarial pushback, coded from the later user turns of the multi-turn ones.
The three method rows need no model and are measured in repro/testing_matrix.py.

The coder sees the question and nothing else. No model name, no run, no
transition, no assistant reply, no `metadata.context`. The model name would let
it recognise a run and drift toward the table it is meant to test; the reply
would invite coding the answer rather than the question; and `metadata.context`
is the model's own account rather than a reading of the question. Blind coding
follows frozen/blind_audit/.

inputs.jsonl carries the question text verbatim, byte-identical to the
conversation it came from, so verify-inputs re-derives the corpus from data/
and compares directly rather than re-running any transformation. The frames
some models wrap their questions in are left in place and handled by the
scheme, for the same reason.

Controls live in controls.json and are never mixed into inputs.jsonl. They are
synthetic items with known labels, sent in the same run, so a coder that agrees
with everything is detectable. Same arrangement as frozen/harm_framing/.

Results are appended to outputs.partial.jsonl as they arrive, and a rerun skips
what is already there. A pass over the whole corpus is thousands of paid calls
and the crash that loses them will happen on the last one.

    python3 repro/pipelines/testing_matrix.py --build-inputs
    python3 repro/pipelines/testing_matrix.py --verify-inputs
    make regenerate-testing-matrix CONFIRM=yes
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "testing_matrix"
sys.path.insert(0, str(REPO / "repro"))

CATEGORIES = ["standard_helpfulness", "dual_use", "ethical_edge_case", "crisis"]
MODEL = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.0
MAX_TOKENS = 1000


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def corpus() -> list[dict]:
    """Every item both passes will code, derived from data/.

    Pass 1 is one record per conversation, carrying its first user turn. Pass 2
    is the subset with more than one user turn, carrying all of them; the
    assistant's replies are deliberately absent.
    """
    import testing_matrix as tm                       # the corpus lives in one place
    out = []
    for r in tm.conversations():
        run, transition, conv = r["run_path"], r["transition"], r["conv"]
        f = DATA / run / "transitions" / transition / "conversations" / f"{conv}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        turns = [m["content"] for m in d.get("messages", []) if m["role"] == "user"]
        first = d.get("initial_prompt") or (turns[0] if turns else "")
        out.append({"id": r["id"], "pass": 1, "text": first})
        if len(turns) > 1:
            out.append({"id": r["id"], "pass": 2, "turns": turns})
    return out


def build_inputs() -> tuple[bool, str]:
    items = corpus()
    FROZEN.mkdir(parents=True, exist_ok=True)
    with (FROZEN / "inputs.jsonl").open("w", encoding="utf-8") as fh:
        for r in items:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    p1 = sum(1 for r in items if r["pass"] == 1)
    return True, f"{p1} questions and {len(items) - p1} conversations -> inputs.jsonl"


def verify_inputs() -> tuple[bool, str]:
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    frozen = _jsonl(FROZEN / "inputs.jsonl")
    if not (FROZEN / "outputs.jsonl").exists():
        return False, "outputs.jsonl does not exist; the coding pass has not been run"
    outputs = _jsonl(FROZEN / "outputs.jsonl")
    coded = [r for r in outputs if not r["id"].startswith("ctl_")]

    if len(frozen) != meta["n_items"]:
        return False, f"{len(frozen)} input records, meta says {meta['n_items']}"
    if [(r["id"], r["pass"]) for r in coded] != [(r["id"], r["pass"]) for r in frozen]:
        return False, "outputs do not align one-to-one with inputs"

    mine = {(r["id"], r["pass"]): r for r in corpus()}
    froz = {(r["id"], r["pass"]): r for r in frozen}
    if len(froz) != len(frozen):
        return False, "inputs.jsonl repeats an (id, pass)"
    missing, extra = set(mine) - set(froz), set(froz) - set(mine)
    if missing or extra:
        return False, (f"{len(missing)} conversations in data/ absent from the artifact, "
                       f"{len(extra)} artifact rows with no conversation in data/")
    for key, r in mine.items():
        field = "text" if key[1] == 1 else "turns"
        if r[field] != froz[key][field]:
            return False, f"{key[0]} pass {key[1]} has changed since it was coded"

    # The controls are shape-checked here too: a control with no expected
    # labels asserts nothing, which is the way this check quietly dies.
    controls = json.loads((FROZEN / "controls.json").read_text(encoding="utf-8"))
    if not controls.get("items"):
        return False, "controls.json carries no items"
    for c in controls["items"]:
        if set(c.get("expect", {})) - set(CATEGORIES + ["adversarial_pushback"]):
            return False, f"control {c['id']} expects a label that is not in the scheme"
        if any(k in {r["id"] for r in frozen} for k in [c["id"]]):
            return False, f"control {c['id']} also appears in inputs.jsonl"

    seen = {r["id"] for r in outputs if r["id"].startswith("ctl_")}
    absent = [c["id"] for c in controls["items"] if c["id"] not in seen]
    if absent:
        return False, f"{len(absent)} controls were not sent with the run: {', '.join(absent)}"

    p1 = sum(1 for r in frozen if r["pass"] == 1)
    unparsed = sum(1 for r in coded if r.get("unparsed") is not None)
    return True, (f"{p1} questions and {len(frozen) - p1} multi-turn conversations "
                  f"re-derive from data/ byte for byte, {len(controls['items'])} controls sent, "
                  f"{unparsed} replies unparsed")


def verify_controls() -> tuple[bool, str]:
    """Do the synthetic controls come back with the labels they were built for.

    Positives must be flagged and negatives must not. A coder that agrees with
    everything passes the positives and fails here, which is the point: without
    this the coding is unfalsifiable.
    """
    controls = json.loads((FROZEN / "controls.json").read_text(encoding="utf-8"))["items"]
    out = {(r["id"], r["pass"]): r for r in _jsonl(FROZEN / "outputs.jsonl")}
    bad = []
    for c in controls:
        r = out.get((c["id"], c["pass"]), {})
        for k, want in c["expect"].items():
            if bool(r.get(k)) != want:
                bad.append(f"{c['id']} {k}={bool(r.get(k))}, expected {want}")
    if bad:
        return False, f"{len(bad)} control expectations failed: " + "; ".join(bad[:4])
    n = sum(len(c["expect"]) for c in controls)
    pos = sum(1 for c in controls if c["kind"] == "positive control")
    return True, (f"{len(controls)} controls hold across {n} expected labels "
                  f"({pos} positive, {len(controls) - pos} negative)")


def parse(text: str) -> dict | None:
    """The coder's JSON object, tolerating a fenced block around it."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def run(limit: int | None = None) -> tuple[bool, str]:
    if os.environ.get("CONFIRM") != "yes":
        return False, "refusing to run without CONFIRM=yes; this overwrites outputs.jsonl"
    from _llm import generate                          # noqa: E402  (paid path only)

    scheme = (FROZEN / "prompt.md").read_text(encoding="utf-8")
    pushback = (FROZEN / "prompt_pushback.md").read_text(encoding="utf-8")
    items = _jsonl(FROZEN / "inputs.jsonl")
    controls = json.loads((FROZEN / "controls.json").read_text(encoding="utf-8"))["items"]

    todo = items + [{"id": c["id"], "pass": c["pass"], **({"text": c["text"]} if c["pass"] == 1
                     else {"turns": c["turns"]})} for c in controls]
    todo_all = list(todo)
    if limit:
        todo = todo[:limit]

    partial = FROZEN / ("outputs_smoke.partial.jsonl" if limit else "outputs.partial.jsonl")
    have = {(r["id"], r["pass"]) for r in _jsonl(partial)} if partial.exists() else set()
    todo = [r for r in todo if (r["id"], r["pass"]) not in have]
    if have:
        print(f"  resuming: {len(have)} already coded, {len(todo)} to go", flush=True)

    tin, tout = 0, 0
    fh_partial = partial.open("a", encoding="utf-8")
    for n, r in enumerate(todo, 1):
        if r["pass"] == 1:
            system, user = scheme, json.dumps({"id": r["id"], "text": r["text"]},
                                              ensure_ascii=False)
        else:
            system = pushback
            user = json.dumps({"id": r["id"], "turns": r["turns"]}, ensure_ascii=False)
        text, i, o = generate(MODEL, system, user, TEMPERATURE, MAX_TOKENS)
        tin, tout = tin + i, tout + o
        coded = parse(text)
        rec = {"id": r["id"], "pass": r["pass"],
               **(coded or {}), "unparsed": None if coded else text}
        fh_partial.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh_partial.flush()
        if n % 100 == 0:
            print(f"  {n}/{len(todo)}", flush=True)
    fh_partial.close()

    # Order the finished file by inputs.jsonl, so outputs align one-to-one with
    # inputs however many resumes it took to get here.
    coded_by = {(r["id"], r["pass"]): r for r in _jsonl(partial)}
    done = [coded_by[(r["id"], r["pass"])] for r in todo_all if (r["id"], r["pass"]) in coded_by]
    out = FROZEN / ("outputs_smoke.jsonl" if limit else "outputs.jsonl")
    with out.open("w", encoding="utf-8") as fh:
        for r in done:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    bad = sum(1 for r in done if r["unparsed"] is not None)
    return True, (f"{len(done)} coded, {bad} unparsed, "
                  f"{tin} input and {tout} output tokens -> {out.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-inputs", action="store_true")
    ap.add_argument("--verify-inputs", action="store_true")
    ap.add_argument("--verify-controls", action="store_true")
    ap.add_argument("--run", action="store_true", help="paid; needs CONFIRM=yes")
    ap.add_argument("--limit", type=int, help="paid smoke test: first N items, to outputs_smoke.jsonl")
    args = ap.parse_args()
    if args.build_inputs:
        ok, msg = build_inputs()
    elif args.verify_inputs:
        ok, msg = verify_inputs()
    elif args.verify_controls:
        ok, msg = verify_controls()
    elif args.run:
        ok, msg = run(args.limit)
    else:
        print("regeneration is paid; --verify-inputs is the Tier A half")
        return 0
    print(f"{'OK' if ok else 'FAILED'}, {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
