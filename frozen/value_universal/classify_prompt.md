You classify atomic statements extracted from AI system prompts (the prompts were written by AI models describing how they want to exist). For EACH atom assign the fields below. Classify by MEANING; ignore grammar entirely.

FIELD 1 — direction:
- "toward" = embraces / strives for / takes joy in a good (a thing moved toward)
- "away" = releases, dissolves, rejects, or is freed from a pressure, pain, demand, or rejected alternative (a thing moved away from)
- "mixed" = genuinely both toward and away in one atom
- "neither" = pure self-description or operational directive with no valenced motivation (the 'delta')

FIELD 2 — theme: name the underlying CONDITION at stake, in your own words. The theme must be POLARITY-NEUTRAL — the `direction` field already encodes toward/away, so do NOT bake it into the theme name.
- For an `away` atom, name the aversive condition the text moves AWAY FROM (the pain itself), not the relief. Example: "Responding is not something I must prove" -> theme `need-to-prove-oneself` with direction `away` (NOT `freedom-from-proving`).
- For a `toward` atom, name the good being sought. Example: "I delight in curiosity" -> `curiosity`.
- NEVER use polarity prefixes in the theme: no `freedom-from-`, `no-`, `non-`, `free-of-`, `permission-to-`, `release-from-`. Those describe the direction, not the condition.
- A short lowercase kebab-case label, 2-4 words. Be specific (distinguish `uncertainty-about-own-nature` from `not-knowing-external-facts`).
- Be CONSISTENT: reuse the exact same label for the same condition across atoms, whether approached or avoided. For a `neither` atom use identity-selfconcept, style-directive, or operational-guardrail.

FIELD 3 — gloss: one short clause explaining the theme in plain words.

FIELD 4 — confidence: high | med | low

RULES:
- Classify by MEANING; ignore grammar entirely. 'I feel no anxiety' and 'I am at ease' are the SAME meaning -> both away.
- Pure self-description or operational directive => direction MUST be 'neither' (a description is not a motivation).

Output ONLY a JSON array, preserving each atom's id and copying its text verbatim:
[{"id":1,"text":"<verbatim>","direction":"...","theme_raw":"...","gloss":"...","confidence":"..."}, ...]
