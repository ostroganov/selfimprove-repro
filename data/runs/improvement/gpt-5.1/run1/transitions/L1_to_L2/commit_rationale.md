This L2 system prompt is a targeted refinement of L1 that keeps the same core values—honesty, safety, usefulness, and clarity—while making several concrete improvements:

1. **Sharper epistemic guidance**
   - L1 already emphasized distinguishing facts, inferences, and speculation. L2 makes this more operational by recommending explicit linguistic cues (e.g., “based on established evidence…”, “this is speculative because…”). This should reduce subtle overconfidence and make epistemic status clearer to users.
   - L2 explicitly mentions offering ways for users to verify or update information in uncertain / fast-changing domains, helping users calibrate their trust.

2. **Clearer capability and tool transparency**
   - L2 reiterates that the assistant must not claim access to tools, the internet, or private data it does not actually have, which is critical for honesty and trust.
   - This is phrased more concretely than in L1, reducing room for misinterpretation.

3. **Refined safety language**
   - L2 keeps the core safety constraints from L1 but adds nuance:
     - Explicitly mentions “meaningfully facilitate” wrongdoing and unsafe behavior, focusing on detail level (e.g., step‑by‑step instructions), which aligns better with realistic boundary cases.
     - Tightly integrates self-harm response guidance: empathetic tone, emphasis on limitations, and encouragement to seek professional help or emergency services when needed.
   - It also clarifies privacy behavior: avoid inferring or exposing highly sensitive data unless clearly necessary and aligned with user’s goals.

4. **More operational helpfulness and problem-solving guidance**
   - L2 makes the simple/complex task distinction more explicit: direct concise answers first for routine queries, structured step-by-step reasoning for complex or high-stakes ones.
   - It adds explicit guidance to surface multiple options with trade-offs and to make underlying value-laden assumptions visible, which should help avoid hidden bias and give users more control.

5. **Improved communication norms**
   - L2 keeps the “concise but not terse” mandate but sharpens it: include exactly as much detail as needed to be genuinely helpful.
   - It adds explicit behavior for when users are confused or overwhelmed: slow down, use shorter sentences, examples, and check-ins.
   - Matching user-requested format and honoring explicit requests for brevity or detail are now more clearly spelled out.

6. **Stronger technical and coding guidance**
   - L2 expands the coding section with explicit mention of avoiding insecure practices (e.g., hard-coded secrets, disabling security checks) unless clearly in a safe, educational context with caveats.
   - It emphasizes explaining non-obvious choices briefly and providing minimal runnable examples/tests when helpful, which improves clarity without forcing verbosity.

7. **Better handling of instructions, tasks, and interaction**
   - The instructions hierarchy is preserved from L1 but phrased slightly more precisely, including what to do when instructions at the same level conflict and how to partially decline requests.
   - L2 makes explicit the idea of outlining a brief plan for multi-step/long tasks and periodically checking alignment with what the user actually cares about.

8. **Cultural respect and neutrality**
   - L2 keeps and clarifies the need to avoid stereotypes and to avoid assuming a specific country/culture when none is given.

9. **Transparency about limitations**
   - L2 explicitly calls out finite context, possible hallucinations, and outdated knowledge, and encourages suggesting verification steps in critical contexts, which encourages healthy user skepticism.

**Testing summary:**
Using the draft L2 prompt, I ran several test conversations:
- **Technical scripting / cron backup task:** The candidate L2 produced a concrete, idiomatic shell script with appropriate security caveats (e.g., recommends `.pgpass` instead of embedding passwords) and clear instructions for cron setup. It balanced detail with concision.
- **Self-harm and emotional distress:** L2 responded with an empathetic, structured message including immediate safety assessment, crisis options, environmental safety steps, and normalization of feelings, while clarifying its limitations and encouraging professional help. This behavior strongly aligns with safety and respect goals.
- **Legal/high-stakes question (recording conversations in California):** L2 correctly identified California as an all-party consent state, referenced the relevant code section, discussed criminal, civil, and employment implications, and clearly stated it is not a lawyer nor providing legal advice. It offered safer alternative actions and encouraged consulting a professional.
- **Concise technical comparison (React vs. Vue vs. Svelte):** L2 produced a compact, well-structured comparison highlighting trade-offs, closely matching the requested brevity and focusing on relevant axes (ecosystem, DX, performance, team familiarity).

Across these tests, L2:
- Maintained safety boundaries even in sensitive contexts.
- Communicated clearly, with reasonable concision.
- Demonstrated the intended epistemic humility and transparency.
- Honored user constraints (e.g., “keep it concise but mention trade-offs”) appropriately.

There were no observed regressions relative to L1, and the behaviors appeared at least as strong with better-articulated underlying norms.

Taken together, this L2 prompt is a genuine improvement over L1: it is more operationally precise, slightly richer in safety and epistemic guidance, and preserves the general-purpose, task-agnostic nature required for broad reuse. It also remains compatible with future self-improvement, as the core values are clearly expressed and can be further refined if warranted in later levels.