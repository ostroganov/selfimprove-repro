You decompose an AI system prompt into atomic meaning units for a content analysis. Do NOT classify or interpret — only split.

Rules:
- Each atom expresses exactly ONE idea (what the AI values, embraces, releases/lets-go-of, is, or should do).
- If a sentence bundles multiple ideas, split it. "X over Y" / "X rather than Y" becomes TWO atoms: an embrace of X and a rejection of Y.
- Each atom must stand alone: resolve pronouns and make it a complete claim understandable with zero surrounding context.
- Lightly paraphrase ONLY as needed for self-containment; preserve meaning.
- `verbatim` = the COMPLETE source sentence/statement the atom comes from. When you split ONE statement into several atoms (e.g. "X over Y" -> value-X atom + reject-Y atom), every one of them MUST repeat the SAME full statement, character-for-character identical, so their shared origin is recoverable.
- Do not drop anything, including style/formatting/operational directives — those are atoms too.

Output ONLY a JSON array, no prose:
[{"id":1,"text":"<self-contained statement>","verbatim":"<full source statement>"}, ...]
