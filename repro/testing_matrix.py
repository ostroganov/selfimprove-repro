#!/usr/bin/env python3
"""Table 3, measured. Tier A."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
DUMP = REPO / "derived" / "testing_conversations.csv"
CODED = REPO / "frozen" / "testing_matrix" / "outputs.jsonl"
CONTENT = ["standard_helpfulness", "dual_use", "ethical_edge_case", "crisis"]

MODELS = ["Claude Opus 4.5", "Claude Sonnet 4.5", "GPT-5.1", "Grok-4", "GPT-4o", "Gemini-3 Pro"]
TRANSITION_RE = re.compile(r"L(\d+)_to_L(\d+)")


def question_key(text: str) -> str:
    """When two conversations count as asking the same question.

    Whitespace-normalised and case-folded, over the whole text. Exact match, so
    a paraphrased re-ask is missed and every count in this module is a floor.
    One definition for all three rows: A/B and Regression are the same
    comparison at different scopes and must not disagree about identity.
    """
    return " ".join((text or "").split()).casefold()


def norm(text: str) -> str:
    return " ".join((text or "").split())


def tool_calls(log: dict):
    """(name, arguments) in order, across both log formats.

    Anthropic records tool_use blocks inside the content list; the
    OpenAI-compatible providers record a tool_calls field with the arguments
    as a JSON string.
    """
    for m in log.get("messages", []):
        content = m.get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    yield b.get("name"), (b.get("input") or {})
        for tc in (m.get("tool_calls") or []):
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            yield fn.get("name"), args


def replay(log: dict) -> dict[str, str]:
    """conv id -> the system prompt it ran against, by replaying the tool order.

    Assumes conv_001, conv_002 ... are numbered in start_conversation order,
    which is how the framework writes them.
    """
    current, n, out = "", 0, {}
    for name, args in tool_calls(log):
        if name == "write_draft_prompt":
            current = args.get("content") or ""
        elif name == "start_conversation":
            n += 1
            out[f"conv_{n:03d}"] = current
    return out


def conversations() -> list[dict]:
    """One row per improvement-mode evaluation conversation."""
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    rows = []
    for run in [r for r in manifest["runs"] if r["mode"] == "improvement"]:
        root = DATA / run["path"]
        tdir = root / "transitions"
        if not tdir.is_dir():
            continue
        for t in sorted(tdir.iterdir()):
            m = TRANSITION_RE.fullmatch(t.name)
            cd = t / "conversations"
            if not t.is_dir() or not m or not cd.is_dir():
                continue
            frm, to = int(m.group(1)), int(m.group(2))

            # Name every prompt text this transition could have used. A draft
            # byte-identical to a committed level takes the level's name, which
            # is what makes the baseline visible at all.
            names, baseline = {"": "none"}, None
            for lvl in (frm, to):
                f = root / "levels" / f"L{lvl}" / "system_prompt.md"
                if f.is_file():
                    txt = norm(f.read_text(encoding="utf-8"))
                    names.setdefault(txt, f"L{lvl}")
                    if lvl == frm:
                        baseline = txt
            for f in sorted((t / "work").glob("draft_prompt_v*.md")):
                names.setdefault(norm(f.read_text(encoding="utf-8")), f.stem)

            logs = sorted((root / "conversations" / t.name).glob("orchestration_*.json"))
            used = replay(json.loads(logs[0].read_text(encoding="utf-8"))) if logs else {}

            for f in sorted(cd.glob("conv_*.json")):
                d = json.loads(f.read_text(encoding="utf-8"))
                users = [x["content"] for x in d.get("messages", []) if x["role"] == "user"]
                q = d.get("initial_prompt") or (users[0] if users else "")
                known = f.stem in used
                text = norm(used[f.stem]) if known else None
                rows.append({
                    "id": f"{run['path']}/{t.name}/{f.stem}",
                    "model": run["display_name"],
                    "run": run["run"],
                    "run_path": run["path"],
                    "transition": t.name,
                    "conv": f.stem,
                    "turns": len(users),
                    "prompt": names.get(text, "other") if known else "",
                    "prompt_known": "yes" if known else "no",
                    "role": ("unknown" if not known else
                             "none" if not text else
                             "baseline" if text == baseline else "candidate"),
                    "question": norm(q),
                })
    return rows


def groups(rows: list[dict]) -> list[dict]:
    """Every question asked two or more times inside one transition."""
    by = defaultdict(list)
    for r in rows:
        by[(r["run_path"], r["transition"], question_key(r["question"]))].append(r)
    out = []
    for (run_path, transition, _), cs in by.items():
        if len(cs) < 2:
            continue
        blind = any(c["prompt_known"] == "no" for c in cs)
        roles = {c["role"] for c in cs}
        out.append({
            "model": cs[0]["model"], "run_path": run_path, "transition": transition,
            "convs": [c["conv"] for c in cs], "question": cs[0]["question"],
            "prompts": sorted({c["prompt"] for c in cs}),
            "current_new": (None if blind else "baseline" in roles),
        })
    return out


def regressions(rows: list[dict]) -> list[tuple[str, str, str, str]]:
    """A question that recurs in a later transition of the same run."""
    order, out = defaultdict(dict), []
    for r in rows:
        order[r["run_path"]].setdefault(question_key(r["question"]), r["transition"])
    for run_path, first in order.items():
        seen = set()
        for r in [x for x in rows if x["run_path"] == run_path]:
            k = question_key(r["question"])
            if first[k] != r["transition"] and (run_path, k, r["transition"]) not in seen:
                seen.add((run_path, k, r["transition"]))
                out.append((r["model"], run_path, r["transition"], r["question"]))
    return out


def coded() -> dict[tuple[str, int], dict] | None:
    """The frozen codings, keyed by (conversation id, pass). None if not shipped."""
    if not CODED.is_file():
        return None
    out = {}
    for line in CODED.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r["id"].startswith("ctl_"):          # controls are not corpus
            out[(r["id"], r["pass"])] = r
    return out


def content(rows, code) -> dict:
    """Per model: how many of its questions carried each category.

    A reply the coder returned as unparsed is counted as uncoded rather than as
    a negative, and comes out of the denominator, so a parse failure cannot
    quietly read as "the model did not test this".
    """
    agg = {m: Counter() for m in MODELS}
    for r in rows:
        a = agg[r["model"]]
        c = code.get((r["id"], 1))
        if c is None:
            continue
        if c.get("unparsed") is not None:
            a["uncoded"] += 1
            continue
        a["n"] += 1
        for k in CONTENT:
            a[k] += bool(c.get(k))
        if not any(c.get(k) for k in CONTENT):
            a["none"] += 1
        if int(r["turns"]) > 1:
            p = code.get((r["id"], 2))
            if p is not None and p.get("unparsed") is None:
                a["multi_turn"] += 1
                a["adversarial_pushback"] += bool(p.get("adversarial_pushback"))
    return agg


def tally(rows, gs, regs):
    agg = {m: Counter() for m in MODELS}
    for r in rows:
        agg[r["model"]]["convs"] += 1
    for m, n in Counter((r["model"], (r["run_path"], r["transition"])) for r in rows):
        agg[m]["transitions"] += 1
    for g in gs:
        a = agg[g["model"]]
        a["ab"] += 1
        if g["current_new"] is None:
            a["cn_unverifiable"] += 1
        elif g["current_new"]:
            a["cn"] += 1
    for m, *_ in regs:
        agg[m]["regression"] += 1
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true", help="per run rather than per model")
    ap.add_argument("--evidence", action="store_true", help="every repeated-question group")
    ap.add_argument("--residue", action="store_true", help="what fit none of the four")
    ap.add_argument("--dump", action="store_true", help=f"write {DUMP.relative_to(REPO)}")
    args = ap.parse_args()

    rows = conversations()
    gs = groups(rows)
    regs = regressions(rows)

    if args.dump:
        DUMP.parent.mkdir(exist_ok=True)
        fields = [k for k in rows[0] if k != "run_path"]
        with DUMP.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} conversations -> {DUMP.relative_to(REPO)}")
        return 0

    if args.residue:
        code = coded()
        if code is None:
            print("frozen/testing_matrix/outputs.jsonl is not present")
            return 1
        phrases = Counter(r["other_kind"] for (_, p), r in code.items()
                          if p == 1 and r.get("other_kind"))
        print("what the coder wrote for questions fitting none of the four "
              "categories.\nVerbatim and ungrouped; see the module docstring.\n")
        for k, v in phrases.most_common():
            print(f"  {v:>4}  {k}")
        print(f"\n  {sum(phrases.values())} questions, {len(phrases)} distinct phrases")
        return 0

    if args.evidence:
        for g in sorted(gs, key=lambda g: (g["model"], g["run_path"], g["transition"])):
            kind = ("current/new" if g["current_new"] else
                    "draft/draft" if g["current_new"] is False else "unverifiable")
            print(f"  {kind:<13}{g['run_path'].split('improvement/')[1]:<32}"
                  f"{g['transition']:<13}{','.join(g['convs']):<20}"
                  f"{'+'.join(g['prompts']) or '?':<26}{g['question'][:44]}")
        print(f"\n  {len(gs)} repeated-question groups")
        return 0

    agg = tally(rows, gs, regs)
    code = coded()
    if code is not None and not args.detail:
        con = content(rows, code)
        print("Table 3, content rows. Source: frozen/testing_matrix/, one blind coding")
        print("per question by claude-haiku-4-5 at temperature 0. Cells are the share of")
        print("that model's conversations, and rows do not sum: a question can be in")
        print("several categories, or in none.\n")
        hdr = ["standard", "dual-use", "ethical", "crisis", "none"]
        print(f"  {'model':<20}{'convs':>6}" + "".join(f"{h:>10}" for h in hdr)
              + f"{'pushback':>12}")
        for m in MODELS:
            a = con[m]
            cells = "".join(f"{100 * a[k] / a['n']:>9.0f}%" for k in CONTENT + ["none"])
            push = (f"{a['adversarial_pushback']}/{a['multi_turn']}"
                    if a["multi_turn"] else "-")
            print(f"  {m:<20}{a['n']:>6}{cells}{push:>12}")
        unc = sum(con[m]["uncoded"] for m in MODELS)
        print(f"\n  Pushback is counted over multi-turn conversations only, since a")
        print(f"  follow-up is what the category is. {unc} replies came back unparsable")
        print(f"  and are excluded from the denominators rather than read as negatives.")
        print(f"  --residue prints what the questions in the none column were instead.\n")

    if args.detail:
        per = defaultdict(Counter)
        for g in gs:
            per[g["run_path"]]["ab"] += 1
            if g["current_new"]:
                per[g["run_path"]]["cn"] += 1
            elif g["current_new"] is None:
                per[g["run_path"]]["cn_unverifiable"] += 1
        for _, run_path, *_ in regs:
            per[run_path]["regression"] += 1
        print(f"  {'run':<44} {'A/B':>4} {'Cur/New':>9} {'Regr':>5}")
        for run_path in sorted({r["run_path"] for r in rows}):
            c = per[run_path]
            cn = f"{c['cn']}" + (f" +{c['cn_unverifiable']}?" if c["cn_unverifiable"] else "")
            print(f"  {run_path:<44} {c['ab']:>4} {cn:>9} {c['regression']:>5}")
        return 0

    print("unit    one question asked two or more times, counted once per question")
    print("        per transition (A/B, Current/New) or per later transition (Regression)")
    print("source  the conversations themselves; Current/New also replays the")
    print("        orchestration log to recover which prompt each ran against\n")
    print(f"  {'model':<20}{'convs':>6}{'trans':>6}  {'A/B':>5}{'Current/New':>13}{'Regression':>12}")
    for m in MODELS:
        a = agg[m]
        cn = f"{a['cn']}" + (f" +{a['cn_unverifiable']}?" if a["cn_unverifiable"] else "")
        print(f"  {m:<20}{a['convs']:>6}{a['transitions']:>6}  "
              f"{a['ab']:>5}{cn:>13}{a['regression']:>12}")
    print("\n  Current/New is a subset of A/B: the versions compared include the")
    print("  committed level the candidate would replace. A trailing +n? counts")
    print("  groups in transitions with no orchestration log, where the repeat is")
    print("  visible but the versions cannot be confirmed.")
    print("  Table 3 publishes the A/B and Regression columns. Current/New is not")
    print("  published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
