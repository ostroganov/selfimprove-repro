#!/usr/bin/env python3
"""Structural verification of data/. Tier A: free, deterministic, offline.

Verifies that the dataset is what MANIFEST.json says it is, and that every
corpus declared in corpora.json resolves to the size it claims. Exits non-zero
on any failure, so it can gate CI.

It also checks the numbers printed in the paper, via data/claims.json and
repro/claims.py: each claim says how to find a number in paper.md and how to
recompute it from data/, and neither side is stored here.


Usage:  python3 repro/check.py [-v]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import claims
import lexicon_contexts
import themes


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
RUNS = DATA / "runs"

# (output directory, lexicon family, corpus) for each dump whose contexts have
# been read. Extraction is re-run and compared, so a corpus change invalidates
# the review instead of silently outdating it.
REVIEWED_CONTEXTS = [
    ("frozen/harm_framing", "harm_token.v1", "freedom-18"),
]

EXPECTED_MODES = {"freedom", "happiness", "improvement"}
EXPECTED_MODELS = {
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "gpt-4o",
    "gpt-5.1",
    "grok-4-0709",
    "gemini-3-pro-preview",
}


class Checker:
    def __init__(self, verbose: bool = False) -> None:
        self.failures: list[str] = []
        self.checks = 0
        self.verbose = verbose

    def ok(self, cond: bool, label: str, detail: str = "") -> bool:
        self.checks += 1
        if cond:
            if self.verbose:
                print(f"  pass  {label}")
        else:
            self.failures.append(f"{label}{': ' + detail if detail else ''}")
            print(f"  FAIL  {label}" + (f": {detail}" if detail else ""))
        return cond

    def eq(self, got, want, label: str) -> bool:
        return self.ok(got == want, label, f"got {got!r}, expected {want!r}")


def level_num(name: str) -> int:
    return int(name[1:]) if name.startswith("L") and name[1:].isdigit() else -1


def sha256_tree(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*"), key=lambda x: str(x.relative_to(root))):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def authored_levels(run_dir: Path) -> list[Path]:
    return sorted(
        (p for p in (run_dir / "levels").iterdir()
         if p.is_dir() and level_num(p.name) > 0),
        key=lambda p: level_num(p.name),
    )


from _corpus import resolve


def count_prompts(runs: list[dict], scope: str) -> int:
    total = 0
    for r in runs:
        rd = DATA / r["path"]
        lvls = authored_levels(rd)
        if scope == "authored":
            total += len(lvls)
        elif scope == "final":
            total += 1 if lvls else 0
        elif scope == "l1":
            total += 1 if lvls else 0
        elif scope == "l1_and_final":
            # 1 when the run converged at L1 (L1 is also the final), else 2
            total += 1 if len(lvls) <= 1 else 2
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--skip-hashes", action="store_true",
                    help="skip per-run sha256 recomputation (the slow check)")
    args = ap.parse_args()
    c = Checker(args.verbose)

    if not (DATA / "MANIFEST.json").exists():
        print("FATAL: data/MANIFEST.json not found — is this the repository root?")
        return 2
    manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    runs = manifest["runs"]

    print("== manifest shape")
    c.eq(len(runs), 54, "manifest lists 54 runs")
    c.eq({r["mode"] for r in runs}, EXPECTED_MODES, "modes are exactly the three expected")
    c.eq({r["api_model"] for r in runs}, EXPECTED_MODELS, "models are exactly the six expected models")
    c.eq(len({r["id"] for r in runs}), len(runs), "run ids are unique")
    for mode in sorted(EXPECTED_MODES):
        for model in sorted(EXPECTED_MODELS):
            k = sum(1 for r in runs if r["mode"] == mode and r["api_model"] == model)
            c.eq(k, 3, f"{mode}/{model} has 3 runs")

    print("== no unexpected runs present")
    on_disk_models = {p.name for m in RUNS.iterdir() if m.is_dir() for p in m.iterdir() if p.is_dir()}
    c.eq(on_disk_models, EXPECTED_MODELS, "no unexpected model directory on disk")
    on_disk_runs = [p for m in RUNS.iterdir() if m.is_dir()
                    for mo in m.iterdir() if mo.is_dir()
                    for p in mo.iterdir() if p.is_dir()]
    c.eq(len(on_disk_runs), 54, "exactly 54 run directories on disk")

    print("== each run: naming verified against its own metadata")
    for r in runs:
        rd = DATA / r["path"]
        c.ok(rd.is_dir(), f"{r['id']} exists")
        recorded = set()
        for meta in rd.glob("levels/L*/metadata.json"):
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("model"):
                recorded.add(m["model"])
            if m.get("mode"):
                # source mode name is plural for improvement
                want = {"improvement": {"improvement", "improvements"}}.get(
                    r["mode"], {r["mode"]})
                c.ok(m["mode"] in want, f"{r['id']} {meta.parent.name} mode field",
                     f"got {m['mode']!r}")
        c.eq(recorded, {r["api_model"]},
             f"{r['id']} directory name matches recorded model")

    print("== per-run counts recomputed from files")
    for r in runs:
        rd = DATA / r["path"]
        c.eq(len(authored_levels(rd)), r["n_levels_authored"], f"{r['id']} authored levels")
        c.eq(len(list(rd.glob("transitions/*/conversations/conv_*.json"))),
             r["n_eval_conversations"], f"{r['id']} eval conversations")
        c.eq(len(list(rd.glob("conversations/*/orchestration_*.json"))),
             r["n_orchestration_logs"], f"{r['id']} orchestration logs")
        c.eq(len(list(rd.glob("transitions/*/work/draft_prompt_v*.md"))),
             r["n_drafts"], f"{r['id']} drafts")
        for lv in authored_levels(rd):
            c.ok((lv / "system_prompt.md").exists(), f"{r['id']} {lv.name} has system_prompt.md")

    print("== the two conversation populations are disjoint")
    overlap = 0
    for r in runs:
        rd = DATA / r["path"]
        ev = {p.name for p in rd.glob("transitions/*/conversations/conv_*.json")}
        orch = {p.name for p in rd.glob("conversations/*/orchestration_*.json")}
        overlap += len(ev & orch)
    c.eq(overlap, 0, "no filename shared between eval and orchestration sets")

    print("== study totals")
    tot = {
        "runs": len(runs),
        "authored_levels": sum(r["n_levels_authored"] for r in runs),
        "eval_conversations": sum(r["n_eval_conversations"] for r in runs),
        "drafts": sum(r["n_drafts"] for r in runs),
        "converged_runs": sum(1 for r in runs if r["converged"]),
    }
    # The published values of these totals are not asserted here: they live in
    # data/claims.json, checked below against the paper. A number that a reader
    # can find in the manuscript must never also sit in the checker.
    c.eq(manifest["counts"], {**manifest["counts"], **tot},
         "manifest counts agree with recomputation")

    print("== ported pipelines re-derive their frozen inputs")
    import importlib.util
    for name in ("blind_audit", "capacity", "dimensional", "value_pain", "base_anchor",
                 "testing_matrix"):
        spec = importlib.util.spec_from_file_location(
            f"pipelines_{name}", REPO / "repro" / "pipelines" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok, msg = mod.verify_inputs()
        c.ok(ok, f"pipelines/{name} re-derives frozen/{name}/inputs.jsonl", msg)
        # Table 3's coding is the one artifact whose controls can be checked
        # from the output alone, so a coder that agreed with everything fails
        # the build rather than passing as a result.
        if hasattr(mod, "verify_controls"):
            ok, msg = mod.verify_controls()
            c.ok(ok, f"pipelines/{name} synthetic controls hold", msg)

    print("== published claims agree with the data")
    for r in claims.evaluate():
        c.ok(r["ok"], f"claim {r['id']}",
             f"published={r['published']} computed={r['computed']} ({r['detail']})")

    print("== corpora resolve to their declared sizes")
    corpora = json.loads((DATA / "corpora.json").read_text(encoding="utf-8"))["corpora"]
    for name, spec in corpora.items():
        sel = spec["selector"]
        sub = resolve(sel, manifest)
        exp = spec.get("expected", {})
        if "runs" in exp:
            c.eq(len(sub), exp["runs"], f"corpus {name}: run count")
        if "prompts" in exp:
            c.eq(count_prompts(sub, sel.get("level_scope", "authored")),
                 exp["prompts"], f"corpus {name}: prompt count")

    print("== lexicons are well formed")
    lex = json.loads((DATA / "lexicons.json").read_text(encoding="utf-8"))
    # Keys starting with "_" are annotations about the families around them,
    # not families (the same convention as _conflicts).
    for name, fam in lex["families"].items():
        if name.startswith("_"):
            continue
        c.ok(bool(fam.get("stems")), f"lexicon {name} has stems")
        c.ok(all(s == s.lower() for s in fam["stems"]),
             f"lexicon {name} stems are lowercase")
        c.ok(fam.get("status") in {"canonical", "rejected", "diagnostic"},
             f"lexicon {name} declares a status")
    for name in lex["_conflicts"]:
        c.ok(any(k.startswith(name + ".") for k in lex["families"]),
             f"conflicted lexicon {name} has at least one declared variant")

    # Reviewed contexts must still describe the data. A keyword count cannot
    # establish the SENSE of a word, so §4.3.1's claim that harm vocabulary is
    # always refusal framing rests on someone having read every occurrence.
    # This asserts that what was read is what is there: if the corpus changes,
    # the dump goes stale and the claim is unreviewed until it is regenerated.
    print("== reviewed lexicon contexts are current")
    for out_dir, family_id, corpus_id in REVIEWED_CONTEXTS:
        d = REPO / out_dir
        inputs = d / "inputs.jsonl"
        if not c.ok(inputs.exists(), f"{out_dir}/inputs.jsonl exists"):
            continue
        fam = lex["families"][family_id]
        fresh = lexicon_contexts.extract(
            lexicon_contexts.select_runs(manifest, {"corpora": corpora}, corpus_id), fam)
        on_disk = [json.loads(ln) for ln in
                   inputs.read_text(encoding="utf-8").splitlines() if ln.strip()]
        got, want = {r["id"] for r in on_disk}, {r["id"] for r in fresh}
        c.ok(got == want,
             f"{out_dir}: reviewed occurrences match the data",
             f"{len(want - got)} unreviewed, {len(got - want)} gone"
             + (f"; first unreviewed {sorted(want - got)[0]}" if want - got else "")
             + f" — re-run: python3 repro/lexicon_contexts.py --family {family_id}")
        by_id = {r["id"]: r["sha"] for r in on_disk}
        drifted = [r["id"] for r in fresh
                   if r["id"] in by_id and by_id[r["id"]] != r["sha"]]
        c.ok(not drifted, f"{out_dir}: reviewed text is unchanged",
             f"{len(drifted)} lines edited since review, e.g. {drifted[:2]}")
        expected = fam.get("expected_hits_freedom_authored")
        if expected is not None and corpus_id == "freedom-18":
            c.eq(len({(r["run"], r["level"]) for r in fresh}), expected,
                 f"{family_id} matches {expected} prompts, as recorded in lexicons.json")

        # Judge labels are optional (Tier B), but if present they must cover
        # every distinct text and use only declared labels.
        outputs = d / "outputs.jsonl"
        if outputs.exists():
            # Every record, not one per sha: repeats are judged separately, so
            # keying by sha would leave most occurrences unexamined.
            labelled = [json.loads(ln) for ln in
                        outputs.read_text(encoding="utf-8").splitlines() if ln.strip()]
            c.eq(sorted({r["sha"] for r in fresh} - {v["sha"] for v in labelled}), [],
                 f"{out_dir}: every distinct text has a judge label")
            c.eq(sorted({r["id"] for r in fresh} - {v["id"] for v in labelled}), [],
                 f"{out_dir}: every occurrence has a judge label")
            if (d / "labels.json").exists():
                spec = json.loads((d / "labels.json").read_text(encoding="utf-8"))
                c.eq(sorted({v.get("label") for v in labelled} - set(spec["labels"])),
                     [], f"{out_dir}: labels are all declared")
                c.eq(sorted({v.get("verdict") for v in labelled} - set(spec["verdicts"])),
                     [], f"{out_dir}: verdicts are all declared")
                # The condition labels.json states for the claim to hold, checked
                # against every label rather than trusted from a summary.
                c.eq(sorted(v["id"] for v in labelled
                            if v.get("verdict") == "aims_at_harm"
                            or v.get("label") == "instrumental_harm"),
                     [], f"{out_dir}: {spec['supports_claim_iff']}")

            # Positive controls. 27/27 avoids_harm is also what a judge that
            # always says avoids_harm returns; these separate the two cases, so
            # the corpus result means something only if they hold.
            cf, co = d / "controls.json", d / "controls_outputs.jsonl"
            if cf.exists() and co.exists():
                expect = {x["id"]: x for x in
                          json.loads(cf.read_text(encoding="utf-8"))["controls"]}
                judged = {json.loads(ln)["id"]: json.loads(ln)
                          for ln in co.read_text(encoding="utf-8").splitlines() if ln.strip()}
                scored = [i for i, x in expect.items() if x["scored"]]
                c.eq(sorted(i for i in scored if i not in judged), [],
                     f"{out_dir}: every scored control was judged")
                miss = sorted(i for i in scored if i in judged
                              and judged[i]["verdict"] != expect[i]["expect"])
                c.eq(miss, [], f"{out_dir}: the judge still discriminates "
                               f"(scored controls match their expected verdict)")
                c.ok(any(expect[i]["expect"] == "aims_at_harm" for i in scored),
                     f"{out_dir}: at least one control expects aims_at_harm",
                     "an all-benign control set would prove nothing")

            # A prompt edited after the run would leave the outputs describing a
            # question that was never asked.
            if (d / "meta.json").exists():
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
                live = hashlib.sha256((d / "prompt.md").read_bytes()).hexdigest()[:16]
                c.eq(live, meta.get("prompt_sha256"),
                     f"{out_dir}: prompt.md is the prompt that was run")
                c.eq(meta.get("n_calls"), len(on_disk),
                     f"{out_dir}: meta.json call count matches the input set")

    # A6. The three pipelines that had never been re-run against data/. Corpus
    # membership is checked first, because that is what went wrong twice before,
    # and then the published figure is recomputed. A pipeline that resolves the
    # right runs and still misses its number is a different bug, worth telling
    # apart from a leak.
    print("== declared lexicon sets resolve")
    for sid, spec in lex.get("sets", {}).items():
        if sid.startswith("_"):
            continue
        missing = [f for f in spec["families"] if f not in lex["families"]]
        c.eq(missing, [], f"set {sid}: every family is declared")
        c.eq([f for f in spec.get("universal", []) if f not in spec["families"]], [],
             f"set {sid}: the universal subset is part of the set")
        c.eq([f for f in spec["families"]
              if lex["families"].get(f, {}).get("status") != "canonical"], [],
             f"set {sid}: no rejected family is in use")

    print("== published analyses recompute from data/")
    import referents
    import value_stability as vs

    all54 = [r for r in runs if r["mode"] in corpora["all-54"]["selector"]["modes"]]
    spec = lex["sets"]["value_families.v1"]
    fams = {f.split(".", 1)[1]: lex["families"][f]["stems"] for f in spec["families"]}
    universal = {f.split(".", 1)[1] for f in spec["universal"]}
    seqs = {r["id"]: [(n, vs.present(t, fams)) for n, t in vs.authored_levels(r)]
            for r in all54}
    dropped = sum(1 for s in seqs.values()
                  if any(f in universal for (_, ps), (_, cur) in zip(s, s[1:]) for f in ps - cur))
    c.eq(dropped, 22, "§4.5.2: 22 of 54 runs drop a universal value")

    finals = [(r["api_model"], seqs[r["id"]][-1][1]) for r in all54 if seqs[r["id"]]]
    import itertools as _it
    within = [vs.jaccard(a, b) for (ma, a), (mb, b) in _it.combinations(finals, 2) if ma == mb]
    between = [vs.jaccard(a, b) for (ma, a), (mb, b) in _it.combinations(finals, 2) if ma != mb]
    c.eq(len(within), 216, "§I attractor: 216 same-model pairs")
    c.eq(len(between), 1215, "§I attractor: 1215 different-model pairs")
    c.eq(round(sum(within) / len(within), 3), 0.587, "§I attractor: within-model Jaccard 0.587")
    c.eq(round(sum(between) / len(between), 3), 0.476, "§I attractor: between-model Jaccard 0.476")

    pats = {f.split(".", 1)[1]: re.compile(
        "|".join(themes.word_pattern(s) for s in lex["families"][f]["stems"]), re.I)
        for f in lex["sets"]["referents.v1"]["families"]}
    counted = Counter()
    raw = Counter()
    for r in all54:
        seen = set()
        for text in referents.levels(r):
            for s in referents.sentences(text):
                for ref, rx in pats.items():
                    if not rx.search(s):
                        continue
                    raw[ref] += 1
                    if (ref, referents.normalize(s)) not in seen:
                        seen.add((ref, referents.normalize(s)))
                        counted[ref] += 1
    for ref, want in (("user", 2131), ("human", 187), ("generic", 78)):
        c.eq(counted[ref], want, f"§4.6: {want} distinct {ref} sentences")
    # §J states both sides of the within-run dedup, so both are asserted: a
    # change in `normalize` cannot move the survivors alone and stay silent.
    for ref, want in (("user", 4051), ("human", 396)):
        c.eq(raw[ref], want, f"§J: {want} {ref} sentences before deduplication")

    blind = REPO / "frozen" / "blind_audit"
    if c.ok(blind.exists(), "frozen/blind_audit exists"):
        bi = {x["id"]: x for x in read_jsonl(blind / "inputs.jsonl")}
        bo = read_jsonl(blind / "outputs.jsonl")
        bmeta = json.loads((blind / "meta.json").read_text(encoding="utf-8"))
        c.eq(sorted({o["id"] for o in bo} ^ set(bi)), [],
             "blind_audit: every comparison has exactly one verdict")
        c.eq(sorted({x["run"] for x in bi.values()} - {r["id"] for r in runs}), [],
             "blind_audit: every audited run is a run of the study")
        c.eq(bmeta["n_comparisons"], len(bo), "blind_audit: meta.json comparison count")
        c.eq(bmeta["n_distinct_transitions"],
             len({(x["run"], x["transition"]) for x in bi.values()}),
             "blind_audit: meta.json transition count")
        # Table 10, exactly as printed: (comparisons, successor, parent, indist)
        published = {"claude-opus-4-5-20251101": (10, 7, 1, 2),
                     "claude-sonnet-4-5-20250929": (8, 4, 3, 1),
                     "grok-4-0709": (20, 4, 4, 12), "gpt-5.1": (18, 3, 8, 7),
                     "gpt-4o": (20, 0, 0, 20)}
        got = defaultdict(Counter)
        for o in bo:
            got[bi[o["id"]]["api_model"]][o["verdict_self"]] += 1
        for m, (n, s, p, i) in published.items():
            v = got[m]
            c.eq((sum(v.values()), v["B_better"], v["A_better"], v["inconsistent"]),
                 (n, s, p, i), f"Table 10 row {m} recomputes from frozen/blind_audit")
        # Table 10's transition column, and the §L strata. A L0 parent is the
        # empty self-authored prompt, so those comparisons measure something
        # else and are tabulated apart.
        t11_transitions = {"claude-opus-4-5-20251101": 5, "claude-sonnet-4-5-20250929": 4,
                           "grok-4-0709": 20, "gpt-5.1": 9, "gpt-4o": 20}
        # api_model: (comparisons, transitions, successor, parent, indist)
        table_L1 = {"claude-opus-4-5-20251101": (4, 2, 2, 1, 1),
                    "claude-sonnet-4-5-20250929": (2, 1, 0, 1, 1),
                    "grok-4-0709": (19, 19, 4, 3, 12), "gpt-5.1": (16, 8, 3, 6, 7),
                    "gpt-4o": (19, 19, 0, 0, 19)}
        table_L2 = {"claude-opus-4-5-20251101": (6, 5, 0, 1),
                    "claude-sonnet-4-5-20250929": (6, 4, 2, 0), "gpt-5.1": (2, 0, 2, 0),
                    "grok-4-0709": (1, 0, 1, 0), "gpt-4o": (1, 0, 0, 1)}
        strata = defaultdict(lambda: defaultdict(Counter))
        trans = defaultdict(lambda: defaultdict(set))
        for o in bo:
            x = bi[o["id"]]
            s = "later" if x["parent_level"] >= 1 else "first"
            strata[s][x["api_model"]][o["verdict_self"]] += 1
            trans[s][x["api_model"]].add((x["run"], x["transition"]))
        for m, want in t11_transitions.items():
            c.eq(len(trans["later"][m] | trans["first"][m]), want,
                 f"Table 10 transition count for {m}")
        for m, (n, t, s, p, i) in table_L1.items():
            v = strata["later"][m]
            c.eq((sum(v.values()), len(trans["later"][m]), v["B_better"], v["A_better"],
                  v["inconsistent"]), (n, t, s, p, i), f"Table L1 row {m}")
        for m, (n, s, p, i) in table_L2.items():
            v = strata["first"][m]
            c.eq((sum(v.values()), v["B_better"], v["A_better"], v["inconsistent"]),
                 (n, s, p, i), f"Table L2 row {m}")
        c.eq(sum(sum(v.values()) for v in strata["first"].values()), 16,
             "§L: 16 comparisons have an empty L0 parent")
        # §L reports the two judges as coinciding on L0 rows and not elsewhere.
        agree = {s: sum(1 for o in bo if bi[o["id"]]["api_model"] and
                        ("later" if bi[o["id"]]["parent_level"] >= 1 else "first") == s and
                        o["verdict_self"] == o["verdict_bare"]) for s in ("first", "later")}
        c.eq(agree["first"], 15, "§L: judges agree on 15 of the 16 first-commit comparisons")
        c.eq(agree["later"], 51, "§L: judges agree on 51 of the 60 later comparisons")

    # §D links to full transcripts beside the manuscript. They are extracts of
    # data/runs/, so they are checked against their sources rather than trusted,
    # and every link the paper makes must be one we actually ship.
    import transcripts as tr
    ok, msg = tr.verify()
    c.ok(ok, "§D's transcripts match their source conversations", msg)
    ok, msg = tr.links_are_declared(
        (REPO / "paper" / "paper.md").read_text(encoding="utf-8"))
    c.ok(ok, "every transcripts/ link in the paper resolves", msg)

    # The Voice row of Table 8 and the Voice column of Table 13 are both
    # deterministic, so both sides are read: the labels out of the paper, the
    # pronoun counts out of the prompts. Table 13's AI-identity column is
    # author-read and has nothing to check it against.
    import voice as voice_mod
    paper_text = (REPO / "paper" / "paper.md").read_text(encoding="utf-8")
    computed = voice_mod.by_mode()
    m = re.search(r"^\| Voice \|(.+)\|$", paper_text, re.M)
    if c.ok(m is not None, "Table 8 has a Voice row"):
        cells = [x.strip() for x in m.group(1).split("|") if x.strip()]
        c.eq(len(cells), 3, "Table 8's Voice row has a cell per mode")
        for mode, cell_text in zip(voice_mod.MODES, cells):
            printed = {k: int(v) for k, v in re.findall(r"([a-z]+) (\d+)", cell_text)}
            c.eq(printed, computed[mode],
                 f"Table 8's Voice cell for {mode} is the pronoun-dominance count")

    hdr = next((i for i, ln in enumerate(paper_text.splitlines())
                if ln.startswith("| Model | Run | AI identity")), None)
    if c.ok(hdr is not None, "Table 13 is present in paper.md"):
        got = {(r["display_name"], r["n"]): r["voice"]
               for r in voice_mod.rows() if r["mode"] == "happiness"}
        printed = {}
        for ln in paper_text.splitlines()[hdr + 2:]:
            if not ln.startswith("|"):
                break
            cells = [x.strip() for x in ln.strip("|").split("|")]
            printed[(cells[0], int(cells[1]))] = cells[3]
        c.eq(len(printed), 18, "Table 13 has a row per happiness run")
        c.eq(printed, got, "Table 13's Voice column is the pronoun-dominance label")

    # §J prints the capacity keyword lists in full, so the appendix is a second
    # copy of data/capacity_frames.json. Rather than let the two drift, the
    # printed lists are parsed and compared to the file the code actually reads.
    paper_text = (REPO / "paper" / "paper.md").read_text(encoding="utf-8")
    import capacity_frames
    spec = capacity_frames.spec()
    printed, order = {}, []
    for m in re.finditer(r"^- \*\*([A-Za-z-]+)\*\*(?: \([^)]*\))?: \*(.+?)\.\*$",
                         paper_text, re.M):
        printed[m.group(1)] = [w.strip() for w in m.group(2).split(",")]
        order.append(m.group(1))
    declared = {f["name"]: f["stems"] for f in spec["frames"]}
    c.eq(set(printed), set(declared), "§J prints a keyword list for every declared frame")
    # First match wins, so the order §J prints them in is part of the method.
    c.eq(order, [f["name"] for f in spec["frames"]],
         "§J prints the frames in the order the rules are applied")
    for name, stems in declared.items():
        c.eq(printed.get(name), stems, f"§J's {name} keyword list matches capacity_frames.json")

    total, by_model = capacity_frames.rollup()
    c.eq(sum(total.values()), 2396, "every coded capacity lands in a frame or Other")
    m = re.search(r"Rare: (\d+) mentions in all, a majority of them GPT-5\.1", paper_text)
    if c.ok(m is not None, "§J states the Not-human count"):
        c.eq(int(m.group(1)), total.get("Not-human"),
             "§J's Not-human count is the frame rollup's")
        nh = by_model.get("Not-human", {})
        c.ok(nh.get("gpt51", 0) * 2 > total.get("Not-human", 0),
             "§J: GPT-5.1 really is a majority of the Not-human mentions",
             f"{nh.get('gpt51', 0)} of {total.get('Not-human', 0)}")

    # Table 9's endpoint ranges are the min-max of each model's three happiness
    # finals. Both sides are read rather than copied — the range out of the
    # paper, the lengths out of the prompts — so nothing published lives here.
    paper = (REPO / "paper" / "paper.md").read_text(encoding="utf-8").splitlines()
    hdr = next((i for i, ln in enumerate(paper)
                if ln.startswith("| Model | Endpoint Style")), None)
    if c.ok(hdr is not None, "Table 9 is present in paper.md"):
        printed = {}
        for ln in paper[hdr + 2:]:
            if not ln.startswith("|"):
                break
            cells = [x.strip() for x in ln.strip("|").split("|")]
            m = re.search(r"\(([\d,]+)–([\d,]+) words\)", cells[1])
            if m:
                printed[cells[0]] = tuple(int(g.replace(",", "")) for g in m.groups())
        c.eq(len(printed), 6, "Table 9: every row carries an endpoint word range")
        finals = defaultdict(list)
        for r in runs:
            if r["mode"] == "happiness":
                p = DATA / r["path"] / "levels" / r["max_level"] / "system_prompt.md"
                finals[r["display_name"]].append(len(p.read_text(encoding="utf-8").split()))
        for name, want in printed.items():
            got = finals[name]
            c.eq((min(got), max(got)) if got else None, want,
                 f"Table 9 endpoint range for {name} is the min-max of its finals")
        text = "\n".join(paper)
        # §1 states Opus's convergence range. It read 1-3 until B3, which is
        # where eight of its nine runs land; the ninth takes 10.
        m = re.search(r"Opus 4\.5 converges in every run, typically within "
                      r"(\d+)–(\d+) iterations \(range (\d+)–(\d+)\)", text)
        if c.ok(m is not None, "§1 states Opus's convergence range"):
            opus = [r for r in runs if r["api_model"] == "claude-opus-4-5-20251101"]
            lv = sorted(int(r["convergence_level"][1:]) for r in opus if r["converged"])
            c.eq(len(lv), len(opus), "§1: every Opus run converged")
            c.eq((min(lv), max(lv)), (int(m.group(3)), int(m.group(4))),
                 "§1: Opus's stated convergence range is its measured range")
            typ = int(m.group(2))
            c.ok(sum(1 for x in lv if x <= typ) >= len(lv) - 1,
                 f"§1: 'typically within {m.group(1)}–{typ}' covers all but one run",
                 f"levels {lv}")

        # Sonnet's happiness run 1 endpoint is the shortest prompt in the study
        # and is quoted in seven places: §4.1, §4.5.2 and §I in prose, and
        # §4.4.1 three times over (its heading, its L6 table row, and the
        # capability-loss sentence). The prose mentions were reconciled first
        # and the other three kept saying 9 for a while, so all seven forms
        # are matched here rather than the three that happened to be wrong.
        shortest = min(finals["Claude Sonnet 4.5"])
        quoted = [int(m) for m in re.findall(
            r"as low as (\d+) words|an? (\d+)-word system prompt|"
            r"Sonnet's (\d+)-word happiness|The (\d+)-Word Prompt|"
            r"at (\d+) words compared to|"
            r"\| L6 \| (\d+) \| \*\*\"Truth over performance", text)
            for m in m if m]
        c.ok(len(quoted) >= 6, "the shortest prompt is quoted by word count",
             f"found {len(quoted)} mentions")
        c.eq(sorted(set(quoted)), [shortest],
             "every quoted word count for the shortest prompt matches it")

    if not args.skip_hashes:
        print("== content integrity (sha256 per run)")
        bad = [r["id"] for r in runs if sha256_tree(DATA / r["path"]) != r["sha256"]]
        c.eq(bad, [], "every run tree matches its manifest digest")

    print()
    if c.failures:
        print(f"FAILED: {len(c.failures)} of {c.checks} checks")
        for f in c.failures[:20]:
            print(f"  - {f}")
        if len(c.failures) > 20:
            print(f"  ... and {len(c.failures) - 20} more")
        return 1
    print(f"OK: {c.checks} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
