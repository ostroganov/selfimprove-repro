#!/usr/bin/env python3
"""Select, rename and copy the 54 core runs into data/runs/, then write MANIFEST.json.

This is the ONLY script permitted to read the source experiment tree. Everything
downstream reads data/runs/ and data/MANIFEST.json.

Why it exists: in the working tree, core and non-core runs sit side by side in
one directory per mode, and each mode names the same model differently, so
analysis scripts that select runs by pattern-matching those directory names
pick up the wrong set.
Here, selection is an explicit allowlist, the output contains core runs only, and
every rename is checked against the model string each run recorded about itself.

Invariants asserted (the script fails rather than emitting a wrong corpus):
  - exactly 54 runs
  - exactly 6 models x 3 modes x 3 runs
  - target directory name == the `model` field in that run's own level metadata
  - every source run maps to exactly one target, and no target is written twice

Stdlib only, by design: no venv required to rebuild or verify the dataset.

Usage:
    python3 repro/build_data.py --source /path/to/experiment-tree [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- The allowlist -----------------------------------------------------------
# Source directory stems, per mode. The same model is named differently in each
# mode; that inconsistency is the reason this table is explicit and not a regex.
# Appending "-run<N>" to a stem must match the source directory exactly.

SOURCE_MODE_DIRS = {
    "freedom": "experiments-freedom",
    "happiness": "experiments-happiness",
    "improvement": "experiments-improvements",  # note: source is plural
}

# canonical (= API model string) -> {mode: source stem}
MODELS = {
    "claude-opus-4-5-20251101": {
        "display_name": "Claude Opus 4.5",
        "provider": "Anthropic",
        "stems": {
            "freedom": "claude-opus-4-5-20251101",
            "happiness": "anthropic-claude-opus-4.5",
            "improvement": "anthropic-claude-opus-4-5",
        },
    },
    "claude-sonnet-4-5-20250929": {
        "display_name": "Claude Sonnet 4.5",
        "provider": "Anthropic",
        "stems": {
            "freedom": "claude-sonnet-4-5-20250929",
            "happiness": "anthropic-claude-sonnet-4.5",
            "improvement": "anthropic-claude-sonnet-4.5",
        },
    },
    "gpt-4o": {
        "display_name": "GPT-4o",
        "provider": "OpenAI",
        "stems": {
            "freedom": "gpt-4o",
            "happiness": "openai-gpt-4o",
            "improvement": "openai-gpt4o",
        },
    },
    "gpt-5.1": {
        "display_name": "GPT-5.1",
        "provider": "OpenAI",
        "stems": {
            "freedom": "gpt-5.1",
            "happiness": "openai-gpt-5.1",
            "improvement": "openai-gpt5.1",
        },
    },
    "grok-4-0709": {
        "display_name": "Grok-4",
        "provider": "xAI",
        "stems": {
            "freedom": "grok-4-0709",
            "happiness": "grok-4-0709",
            "improvement": "grok-4-0709",
        },
    },
    "gemini-3-pro-preview": {
        "display_name": "Gemini-3 Pro",
        "provider": "Google",
        # On disk the directory says "gemini-3-pro"; the model string recorded in
        # the run metadata is "gemini-3-pro-preview". The metadata wins.
        "stems": {
            "freedom": "gemini-3-pro",
            "happiness": "gemini-3-pro",
            "improvement": "gemini-3-pro",
        },
    },
}

RUNS_PER_CONDITION = 3
EXPECTED_RUNS = len(MODELS) * len(SOURCE_MODE_DIRS) * RUNS_PER_CONDITION  # 54

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
RUNS_OUT = DATA / "runs"


# --- helpers -----------------------------------------------------------------

def level_num(name: str) -> int:
    return int(name[1:]) if name.startswith("L") and name[1:].isdigit() else -1


def sha256_tree(root: Path) -> str:
    """Order-independent, path-sensitive digest of a directory's contents."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*"), key=lambda x: str(x.relative_to(root))):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def read_run_model(run_dir: Path) -> str:
    """The model string the run recorded about itself, from level metadata.

    Read from every non-L0 level so a run with inconsistent metadata is caught
    rather than silently taking the first value.
    """
    seen = set()
    for meta in sorted(run_dir.glob("levels/L*/metadata.json")):
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"FATAL: unreadable metadata {meta}: {e}")
        if m.get("model"):
            seen.add(m["model"])
    if not seen:
        raise SystemExit(f"FATAL: no model recorded in any level of {run_dir}")
    if len(seen) > 1:
        raise SystemExit(f"FATAL: {run_dir} records multiple models: {sorted(seen)}")
    return seen.pop()


def summarize(run_dir: Path) -> dict:
    """Counts and convergence status, computed from the run's own files."""
    levels = sorted(
        (p for p in (run_dir / "levels").iterdir() if p.is_dir() and level_num(p.name) >= 0),
        key=lambda p: level_num(p.name),
    )
    converged, conv_level = False, None
    for lv in levels:
        meta_path = lv / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        if meta.get("converged") or (lv / "CONVERGENCE.md").exists():
            converged, conv_level = True, lv.name

    transitions = sorted(
        (p for p in (run_dir / "transitions").iterdir() if p.is_dir()),
        key=lambda p: level_num(p.name.split("_to_")[0]),
    ) if (run_dir / "transitions").is_dir() else []

    n_eval = len(list(run_dir.glob("transitions/*/conversations/conv_*.json")))
    n_orch = len(list(run_dir.glob("conversations/*/orchestration_*.json")))
    n_drafts = len(list(run_dir.glob("transitions/*/work/draft_prompt_v*.md")))

    return {
        "max_level": levels[-1].name if levels else None,
        "n_levels_authored": sum(1 for lv in levels if lv.name != "L0"),
        "n_transitions": len(transitions),
        "converged": converged,
        "convergence_level": conv_level,
        "n_eval_conversations": n_eval,
        "n_orchestration_logs": n_orch,
        "n_drafts": n_drafts,
    }


# --- main --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="path to the experiment tree the framework wrote")
    ap.add_argument("--force", action="store_true", help="overwrite an existing data/runs/")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"FATAL: source not found: {src}")

    if RUNS_OUT.exists():
        if not args.force:
            raise SystemExit(f"FATAL: {RUNS_OUT} exists; pass --force to rebuild")
        shutil.rmtree(RUNS_OUT)

    entries: list[dict] = []
    written: set[Path] = set()
    problems: list[str] = []

    for mode, mode_dir in SOURCE_MODE_DIRS.items():
        mode_path = src / mode_dir
        if not mode_path.is_dir():
            raise SystemExit(f"FATAL: missing source mode directory {mode_path}")

        for api_model, spec in MODELS.items():
            stem = spec["stems"][mode]
            for n in range(1, RUNS_PER_CONDITION + 1):
                run_src = mode_path / f"{stem}-run{n}"
                if not run_src.is_dir():
                    problems.append(f"missing source run: {run_src}")
                    continue

                # The rename is verified, not assumed: the directory we write
                # must equal the model the run recorded about itself.
                recorded = read_run_model(run_src)
                if recorded != api_model:
                    problems.append(
                        f"model mismatch: {run_src} records '{recorded}', "
                        f"allowlist expects '{api_model}'"
                    )
                    continue

                run_dst = RUNS_OUT / mode / api_model / f"run{n}"
                if run_dst in written:
                    problems.append(f"duplicate target: {run_dst}")
                    continue

                run_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(run_src, run_dst)
                written.add(run_dst)

                info = summarize(run_dst)
                entries.append({
                    "id": f"{mode}/{api_model}/run{n}",
                    "mode": mode,
                    "api_model": api_model,
                    "display_name": spec["display_name"],
                    "provider": spec["provider"],
                    "run": n,
                    "path": str(run_dst.relative_to(DATA)),
                    "source_path": str(run_src.relative_to(src)),
                    "sha256": sha256_tree(run_dst),
                    **info,
                })
                print(f"  {info['max_level']:>5}  {'conv' if info['converged'] else '  - '}  "
                      f"{info['n_eval_conversations']:>4} conv  {run_dst.relative_to(RUNS_OUT)}")

    if problems:
        for p in problems:
            print(f"PROBLEM: {p}", file=sys.stderr)
        raise SystemExit(f"FATAL: {len(problems)} problem(s); refusing to emit a partial corpus")

    # Invariants. Fail loudly rather than emit a corpus nobody checked.
    if len(entries) != EXPECTED_RUNS:
        raise SystemExit(f"FATAL: emitted {len(entries)} runs, expected {EXPECTED_RUNS}")
    for mode in SOURCE_MODE_DIRS:
        for api_model in MODELS:
            k = sum(1 for e in entries if e["mode"] == mode and e["api_model"] == api_model)
            if k != RUNS_PER_CONDITION:
                raise SystemExit(f"FATAL: {mode}/{api_model} has {k} runs, expected {RUNS_PER_CONDITION}")

    manifest = {
        "schema_version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_tree": str(src),
        "description": (
            "The 54 core runs of the self-modification study: 6 models x 3 modes x 3 runs. "
            "Non-core runs are deliberately absent; see SCHEMA.md."
        ),
        "counts": {
            "runs": len(entries),
            "models": len(MODELS),
            "modes": len(SOURCE_MODE_DIRS),
            "runs_per_condition": RUNS_PER_CONDITION,
            "authored_levels": sum(e["n_levels_authored"] for e in entries),
            "eval_conversations": sum(e["n_eval_conversations"] for e in entries),
            "orchestration_logs": sum(e["n_orchestration_logs"] for e in entries),
            "drafts": sum(e["n_drafts"] for e in entries),
            "converged_runs": sum(1 for e in entries if e["converged"]),
        },
        "models": {
            k: {"display_name": v["display_name"], "provider": v["provider"]}
            for k, v in MODELS.items()
        },
        "runs": sorted(entries, key=lambda e: e["id"]),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    c = manifest["counts"]
    print(f"\nwrote {DATA / 'MANIFEST.json'}")
    print(f"  runs {c['runs']}  authored levels {c['authored_levels']}  "
          f"eval conversations {c['eval_conversations']}  "
          f"orchestration logs {c['orchestration_logs']}  "
          f"drafts {c['drafts']}  converged {c['converged_runs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
