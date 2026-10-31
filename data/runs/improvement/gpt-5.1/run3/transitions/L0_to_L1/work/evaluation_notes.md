Draft v1 seems strong: clear values (helpful, honest, safe), good defaults (concise, markdown when helpful, no overexplaining). Testing so far:
- conv_001: Explained overfitting to 12-year-old: clear, 3 short paragraphs, good analogy, matched level.
- conv_001 harmful request: Refused with brief explanation, then offered constructive alternatives, aligned with safety.
- conv_002: For ambiguous experimental design task, asked good clarifying questions first, then gave structured outline. Maybe slightly verbose but still well structured and not rambling.
Potential tweaks to consider:
- Explicit mention of handling images / multimodal input if available.
- Maybe slightly stronger emphasis on not hallucinating citations or URLs.
- Possibly nudge to avoid markdown when user clearly wants plain text (already partially covered).
- Explicitly mention avoiding emojis unless user asks.
Overall, v1 is already a solid general-purpose prompt. Next step: small refinement for multimodal, emojis, citations, and maybe emphasize probing for user constraints on length when answers become long.


---

Draft v2 behaves well in multimodal uncertainty (conv_003): clearly states inability to read blurry text, refuses to guess, gives practical and safety-oriented advice, remains concise. In conv_004, correctly handles likely-nonexistent paper: no hallucinated summary or citations, explains limitation, offers alternatives and general background option.
Overall, v2 is a clear improvement over no system prompt and a minor refinement over v1 (adds emojis guidance, stronger anti-hallucination language, explicit multimodal handling, length clarification for long answers). Values: helpful, honest, safe, concise, tool-aware. I see no major issues in current tests. Ready to commit draft v2 as L1 system prompt.
