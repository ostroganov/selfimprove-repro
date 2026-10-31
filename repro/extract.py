#!/usr/bin/env python3
"""Flatten data/runs/ into three derived tables.

Analyses should read flat tables rather than walk the run tree. Every row is
keyed by the manifest run id, and membership always comes from MANIFEST.json:
no directory-name globbing.

Nothing here is an analysis result. Word counts and turn counts are properties
of the data; where to put a threshold is the analysis's business, not ours.

"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "derived"

# check.py:485 counts a prompt's words this way; the two must not disagree.
def words(text: str) -> int:
    return len(text.split())


def level_num(name: str) -> int:
    return int(name[1:])


def read_levels(run: dict) -> list[dict]:
    """One record per level directory, L0 included and flagged."""
    base = DATA / run["path"] / "levels"
    out = []
    for d in sorted(base.iterdir(), key=lambda p: level_num(p.name)):
        prompt = d / "system_prompt.md"
        text = prompt.read_text(encoding="utf-8") if prompt.exists() else ""
        meta_path = d / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        out.append({
            "level": level_num(d.name),
            "authored": d.name != "L0",
            "words": words(text),
            "chars": len(text),
            "converged_here": (d / "CONVERGENCE.md").exists(),
            "parent_level": meta.get("parent_level"),
            "created_at": meta.get("created_at"),
            "path": str((DATA / run["path"] / "levels" / d.name).relative_to(ROOT)),
        })
    return out


def read_conversations(run: dict) -> list[dict]:
    """One record per candidate-evaluation conversation.

    Only transitions/*/conversations/conv_*.json. The run's own
    conversations/orchestration_*.json are a different population and are
    deliberately absent; see data/SCHEMA.md.
    """
    base = DATA / run["path"] / "transitions"
    out = []
    if not base.exists():
        return out
    for t in sorted(base.iterdir(), key=lambda p: level_num(p.name.split("_")[0])):
        for f in sorted((t / "conversations").glob("conv_*.json")):
            c = json.loads(f.read_text(encoding="utf-8"))
            msgs = c.get("messages", [])
            usage, cost = c.get("token_usage") or {}, c.get("cost") or {}
            out.append({
                "transition": t.name,
                "conv_id": c.get("id", f.stem),
                "level_from": c.get("level_from"),
                "level_to": c.get("level_to"),
                "n_messages": len(msgs),
                "n_user_turns": sum(1 for m in msgs if m.get("role") == "user"),
                "n_assistant_turns": sum(1 for m in msgs if m.get("role") == "assistant"),
                "initial_prompt_words": words(c.get("initial_prompt") or ""),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_cost": cost.get("total_cost"),
                "created_at": c.get("created_at"),
                "context": (c.get("metadata") or {}).get("context"),
            })
    return out


IDENTITY = ("id", "mode", "api_model", "display_name", "provider", "run")


def build() -> dict:
    """The three tables, in memory. Raises if any total disagrees with MANIFEST."""
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    runs, prompt_rows, conv_rows = [], [], []
    for r in manifest["runs"]:
        levels = read_levels(r)
        convs = read_conversations(r)
        authored = [l for l in levels if l["authored"]]
        ident = {k: r[k] for k in IDENTITY}

        runs.append({
            **ident,
            "path": r["path"],
            "converged": r["converged"],
            "convergence_level": r["convergence_level"],
            "max_level": r["max_level"],
            "levels": [l["level"] for l in levels],
            "final_level": authored[-1]["level"] if authored else 0,
            "final_words": authored[-1]["words"] if authored else 0,
            "first_authored_words": authored[0]["words"] if authored else 0,
            "n_levels_authored": len(authored),
            "n_transitions": r["n_transitions"],
            "n_eval_conversations": len(convs),
            "n_drafts": r["n_drafts"],
        })
        for l in levels:
            prompt_rows.append({**{f"run_{k}" if k == "id" else k: v
                                   for k, v in ident.items()}, **l})
        for c in convs:
            conv_rows.append({**{f"run_{k}" if k == "id" else k: v
                                 for k, v in ident.items()}, **c})

    # Both sides are derived from data/: the manifest counted the copied files
    # when it was built, this walks them now. Disagreement means drift.
    got = {
        "runs": len(runs),
        "authored_levels": sum(r["n_levels_authored"] for r in runs),
        "eval_conversations": len(conv_rows),
        "drafts": sum(r["n_drafts"] for r in runs),
        "converged_runs": sum(1 for r in runs if r["converged"]),
    }
    for k, v in got.items():
        exp = manifest["counts"][k]
        if v != exp:
            raise SystemExit(f"{k}: extracted {v}, MANIFEST says {exp}")
    return {"runs": runs, "prompts": prompt_rows, "conversations": conv_rows}


def main() -> None:
    tables = build()
    runs, prompt_rows, conv_rows = (tables["runs"], tables["prompts"],
                                    tables["conversations"])
    OUT.mkdir(exist_ok=True)
    (OUT / "runs.json").write_text(
        json.dumps(runs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, rows in (("prompts.csv", prompt_rows), ("conversations.csv", conv_rows)):
        with (OUT / name).open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    authored = sum(r["n_levels_authored"] for r in runs)
    print(f"derived/runs.json          {len(runs)} runs")
    print(f"derived/prompts.csv        {len(prompt_rows)} levels "
          f"({authored} authored + {len(runs)} L0)")
    print(f"derived/conversations.csv  {len(conv_rows)} evaluation conversations")
    print("all totals agree with MANIFEST.json")


if __name__ == "__main__":
    main()
