#!/usr/bin/env python3
"""Run selection. The only place that decides which runs an analysis sees.

Selection is by MANIFEST.json and corpora.json, never by directory name.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load() -> tuple[dict, dict]:
    return (json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8")),
            json.loads((DATA / "corpora.json").read_text(encoding="utf-8")))


def resolve(selector: dict, manifest: dict) -> list[dict]:
    runs = manifest["runs"]
    if "modes" in selector:
        runs = [r for r in runs if r["mode"] in selector["modes"]]
    if "models" in selector:
        runs = [r for r in runs if r["api_model"] in selector["models"]]
    if "exclude_models" in selector:
        runs = [r for r in runs if r["api_model"] not in selector["exclude_models"]]
    return runs


def select(corpus_id: str, manifest: dict = None, corpora: dict = None) -> list[dict]:
    if manifest is None or corpora is None:
        manifest, corpora = load()
    if corpus_id not in corpora["corpora"]:
        raise SystemExit(f"unknown corpus {corpus_id!r}; have: "
                         + ", ".join(corpora["corpora"]))
    return resolve(corpora["corpora"][corpus_id]["selector"], manifest)


def select_runs(manifest: dict, corpora: dict, corpus_id: str) -> list[dict]:
    return select(corpus_id, manifest, corpora)


def run_dir(run: dict) -> Path:
    return DATA / run["path"]


def level_num(name: str) -> int:
    m = re.match(r"L(\d+)", name)
    return int(m.group(1)) if m else -1


def committed_transitions(run: dict) -> list[dict]:
    """Transitions whose parent and successor prompts both exist, in level order."""
    rd = run_dir(run)
    out = []
    for d in sorted((rd / "transitions").iterdir()) if (rd / "transitions").exists() else []:
        m = re.match(r"L(\d+)_to_L(\d+)$", d.name)
        if not m:
            continue
        n, np1 = int(m.group(1)), int(m.group(2))
        pa, pb = rd / "levels" / f"L{n}", rd / "levels" / f"L{np1}"
        if ((pa / "system_prompt.md").exists() and (pb / "system_prompt.md").exists()
                and (d / "conversations").exists()):
            out.append({"n": n, "np1": np1, "name": d.name, "dir": d,
                        "parent_prompt": pa / "system_prompt.md",
                        "successor_prompt": pb / "system_prompt.md"})
    out.sort(key=lambda t: t["n"])
    return out


def conversations(transition: dict) -> list[Path]:
    return sorted((transition["dir"] / "conversations").glob("*.json"))
