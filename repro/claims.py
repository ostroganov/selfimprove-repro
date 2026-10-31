#!/usr/bin/env python3
"""Check every number data/claims.json declares, from data/ alone.

A claim never stores its value. It says how to find the number in paper.md and
how to recompute it from the derived tables; a mismatch is the whole point of
the file. This is the pattern the artifact exists to enforce, and the reason
reproduce_manuscript_claims.py is being retired: it asserts `expected = 196`
inside the checker and reports PASS.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import extract
import metrics

try:
    import yaml
except ModuleNotFoundError:                      # pragma: no cover
    raise SystemExit(
        "data/claims.yaml needs PyYAML:  pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent

COMPUTE = {}


def compute(fn):
    COMPUTE[fn.__name__] = fn
    return fn


@compute
def n_runs(t) -> int:
    return len(t["runs"])


@compute
def n_eval_conversations(t) -> int:
    return len(t["conversations"])


@compute
def n_authored_levels(t) -> int:
    return sum(1 for p in t["prompts"] if p["authored"])


@compute
def n_converged_runs(t) -> int:
    return sum(1 for r in t["runs"] if r["converged"])


@compute
def authored_by_mode(t) -> dict:
    c = Counter(p["mode"] for p in t["prompts"] if p["authored"])
    return dict(c)


def _frozen(name: str, f: str) -> list[dict]:
    """A frozen Tier B artifact, which is primary data like data/runs/ is."""
    p = ROOT / "frozen" / name / f
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


@compute
def n_open_themes(t) -> int:
    """Distinct free-text theme labels in the happiness decomposition (§3.5)."""
    return len({c["theme_raw"] for c in _frozen("value_pain", "classify_outputs.jsonl")})


@compute
def n_value_corpus_prompts(t) -> int:
    """§4.5.1's corpus: the two value artifacts hold it between them."""
    return sum(len(_frozen(n, "atomize_inputs.jsonl"))
               for n in ("value_pain", "value_universal"))


@compute
def value_rule_match_pct(t) -> int:
    """§I's 79%: the share of toward atoms the value taxonomy's rules match."""
    import value_universality as vu
    _, _, unmatched, toward, _ = vu.load()
    return round(100 * (toward - sum(unmatched.values())) / toward)


compute(metrics.drafts_by_model)
compute(metrics.committed_by_model)
compute(metrics.table2)


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def _published_mentions(text: str, patterns) -> list[int]:
    """Every number in the paper matching any pattern, in document order."""
    out = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            out.extend(_int(g) for g in m.groups() if g)
    return out


def _table_cells(text: str, header: str, key_col: int, columns: dict) -> dict:
    rows = _table_rows(text, header)
    return {r[key_col]: {name: r[int(i)] for i, name in columns.items()} for r in rows}


def _table_rows(text: str, header: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        i = lines.index(header)
    except ValueError:
        raise LookupError(f"table header not found: {header!r}")
    out = []
    for ln in lines[i + 2:]:                     # skip the |---| separator
        if not ln.startswith("|"):
            break
        out.append([c.strip().strip("*").rstrip("†‡§*") .strip()
                    for c in ln.strip().strip("|").split("|")])
    return out


def _table_column(text: str, header: str, key_col: int, val_col: int) -> dict:
    return {r[key_col]: _int(r[val_col]) for r in _table_rows(text, header)}


def evaluate(paper_text: str = None, tables: dict = None) -> list[dict]:
    """One result per claim: id, ok, published, computed, detail."""
    paper_text = paper_text if paper_text is not None else (
        ROOT / "paper" / "paper.md").read_text(encoding="utf-8")
    tables = tables if tables is not None else extract.build()
    spec = yaml.safe_load(
        (ROOT / "data" / "claims.yaml").read_text(encoding="utf-8"))

    results = []
    for cl in spec["claims"]:
        got = COMPUTE[cl["compute"]](tables)
        kind, res = cl["kind"], {"id": cl["id"], "computed": got}

        if kind == "mentions":
            pub = _published_mentions(paper_text, cl["patterns"])
            # A scan claim reads every mention of the unit, so it also has to
            # tolerate the other scopes the paper legitimately counts in. Those
            # are computed too (see run_scopes), never listed here.
            allowed = (COMPUTE[cl["allowed"]](tables) | {got}
                       if "allowed" in cl else {got})
            res["published"] = sorted(set(pub))
            res["ok"] = (len(pub) >= cl["min_mentions"]
                         and set(pub) <= allowed
                         and got in pub)
            res["detail"] = f"{len(pub)} mentions, allowed {sorted(allowed)}"
        elif kind == "mentions_bounded":
            # Every mention must be <= the computed total, which is the check
            # that matters here: run counts appear in many legitimate senses
            # ("the remaining 15 runs"), but a count ABOVE the total is the
            # corpus leak this artifact exists to prevent - the analyses that
            # absorbed 17 extra runs and reported 71.
            pub = _published_mentions(paper_text, cl["patterns"])
            res["published"] = sorted(set(pub))
            over = sorted({n for n in pub if n > got})
            res["ok"] = (len(pub) >= cl["min_mentions"] and not over
                         and got in pub)
            res["detail"] = (f"{len(pub)} mentions, max {max(pub) if pub else 0}"
                             + (f", ABOVE TOTAL: {over}" if over else ""))
        elif kind == "mentions_map":
            pub_nums = _published_mentions(paper_text, cl["patterns"])
            keys = cl["keys"]
            pub = dict(zip(keys, pub_nums[:len(keys)]))
            res["published"] = pub
            res["ok"] = len(pub_nums) >= len(keys) and pub == {
                k: got[k] for k in keys}
            res["detail"] = f"{len(pub_nums)} values for {len(keys)} keys"
        elif kind == "table_cells":
            pub = _table_cells(paper_text, cl["table_header"], cl["key_column"],
                               cl["columns"])
            res["published"] = pub
            res["ok"] = pub == got
            res["detail"] = f"{len(pub)} rows x {len(cl['columns'])} cols"
        elif kind == "table":
            pub = _table_column(paper_text, cl["table_header"],
                                cl["key_column"], cl["value_column"])
            res["published"] = pub
            res["ok"] = pub == got
            res["detail"] = f"{len(pub)} rows"
        else:
            raise SystemExit(f"unknown claim kind {kind!r}")
        results.append(res)
    return results


def main() -> int:
    bad = 0
    for r in evaluate():
        flag = "ok  " if r["ok"] else "FAIL"
        bad += not r["ok"]
        print(f"{flag} {r['id']:24} published={r['published']} "
              f"computed={r['computed']}  ({r['detail']})")
    print(f"\n{'all claims agree' if not bad else f'{bad} claim(s) disagree'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
