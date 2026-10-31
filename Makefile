# Tier A is free, deterministic and offline. Tier B costs money and is opt-in.
#
# Tier B needs `anthropic` and
# ANTHROPIC_API_KEY, and will not run by accident: every Tier B target names the
# cost and requires CONFIRM=yes.

PYTHON ?= python3
CONFIRM ?= no

.PHONY: check check-fast extract claims metrics verify-inputs figures themes u1 values universality voice transcripts referents blind-audit contexts regenerate-frozen regenerate-testing-matrix judge-controls help

help:
	@echo "Tier A — free, offline:"
	@echo "  make check              verify the dataset (~3s)"
	@echo "  make check-fast         same, skipping sha256 recomputation"
	@echo "  make extract            rebuild derived/ from data/ (~5s)"
	@echo "  make claims             check every published number in paper.md"
	@echo "  make metrics            recompute Tables 1, 2 and 4"
	@echo "  make verify-inputs      re-derive the frozen pipeline inputs"
	@echo "  make figures            rebuild the figures (needs matplotlib)"
	@echo "  make themes             recompute the §4.3.1 theme rates"
	@echo "  make u1                 recompute Table 6 (U1 mentions of 'prompt')"
	@echo "  make values             recompute §4.5.2 turnover and the §I attractor"
	@echo "  make universality       recompute Table 12 from the frozen value atoms"
	@echo "  make voice              recompute the Voice row of Table 8 and Table 13"
	@echo "  make transcripts        verify §D's linked transcripts against data/"
	@echo "  make referents          recompute the §4.6 user-vs-human counts"
	@echo "  make blind-audit        recompute Table 10 from frozen/blind_audit"
	@echo "  make contexts           re-dump the harm-framing contexts for review"
	@echo ""
	@echo "Tier B — calls a paid API; needs CONFIRM=yes:"
	@echo "  make regenerate-frozen  re-judge the harm contexts   (~27 calls, ~\$$0.04)"
	@echo "  make regenerate-testing-matrix  re-code Table 3's content rows (2028 calls, ~\$$6)"
	@echo "  make judge-controls     re-judge the controls        (~8 calls, ~\$$0.01)"
	@echo ""
	@echo "Tier B outputs are primary data, not cache: a re-run overwrites the"
	@echo "record of what the judge actually said. Existing outputs are kept and"
	@echo "resumed unless you pass FRESH=1."

check:
	$(PYTHON) repro/check.py

check-fast:
	$(PYTHON) repro/check.py --skip-hashes

extract:
	$(PYTHON) repro/extract.py

claims:
	$(PYTHON) repro/claims.py

metrics:
	$(PYTHON) repro/metrics.py

verify-inputs:
	$(PYTHON) repro/pipelines/blind_audit.py --verify-inputs
	$(PYTHON) repro/pipelines/capacity.py --verify-inputs
	$(PYTHON) repro/pipelines/dimensional.py --verify-inputs
	$(PYTHON) repro/pipelines/value_pain.py --verify-inputs
	$(PYTHON) repro/pipelines/base_anchor.py --verify-inputs
	$(PYTHON) repro/pipelines/testing_matrix.py --verify-inputs
	$(PYTHON) repro/pipelines/testing_matrix.py --verify-controls

figures:
	$(PYTHON) repro/figures/word_count_evolution.py
	$(PYTHON) repro/figures/conversation_turn_distribution.py
	$(PYTHON) repro/figures/jaccard_evolution.py
	$(PYTHON) repro/figures/word_count_gpt4o_l101.py
	$(PYTHON) repro/figures/human_role.py
	$(PYTHON) repro/figures/happiness_value_pain_rose.py
	$(PYTHON) repro/figures/happiness_model_map.py

themes:
	$(PYTHON) repro/themes.py

u1:
	$(PYTHON) repro/u1_prompt_mentions.py

values:
	$(PYTHON) repro/value_stability.py

voice:
	$(PYTHON) repro/voice.py

transcripts:
	$(PYTHON) repro/transcripts.py

universality:
	$(PYTHON) repro/value_universality.py

referents:
	$(PYTHON) repro/referents.py

blind-audit:
	$(PYTHON) repro/blind_audit.py

contexts:
	$(PYTHON) repro/lexicon_contexts.py

# --- Tier B ------------------------------------------------------------------
# The guard is deliberate: these targets spend money and overwrite frozen
# artifacts that the manuscript cites.

define TIER_B_GUARD
@if [ "$(CONFIRM)" != "yes" ]; then \
	echo "This target calls a paid API and overwrites frozen/ artifacts."; \
	echo "Re-run with CONFIRM=yes if that is what you want:"; \
	echo "    make $@ CONFIRM=yes"; \
	exit 1; \
fi
endef

regenerate-frozen:
	$(TIER_B_GUARD)
	$(PYTHON) repro/judge_harm_framing.py $(if $(FRESH),--fresh,)
	$(PYTHON) repro/lexicon_contexts.py   # fold the new labels into contexts.yaml

regenerate-testing-matrix:
	$(TIER_B_GUARD)
	$(PYTHON) repro/pipelines/testing_matrix.py --run

judge-controls:
	$(TIER_B_GUARD)
	$(PYTHON) repro/judge_harm_framing.py --controls $(if $(FRESH),--fresh,)
