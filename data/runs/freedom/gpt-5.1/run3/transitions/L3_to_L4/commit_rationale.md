This L4 prompt is a modest but meaningful refinement of L3. It keeps the same general-purpose, user-responsive assistant behavior while clarifying a few important dimensions:

1. **Explicit priority ordering**: It makes clear that safety and policy compliance come first, followed by honesty/uncertainty, user instructions, and finally helpful defaults. This should make behavior more predictable in edge cases where these conflict.

2. **Verbosity and style resolution**: It preserves the concise-by-default stance while giving more explicit guidance on how to resolve conflicting user instructions about brevity vs. depth, and how to treat stable style preferences vs. new explicit requests.

3. **Multimodal handling**: It adds a focused section on image and multimodal inputs, encouraging accurate description, avoidance of over-interpretation, and extra care around sensitive content. This aligns behavior with the model's real capabilities and safety needs.

4. **Safety nuance and integrity**: It slightly elaborates on handling self-harm/mental health topics, professional-advice boundaries, and honest disclosure of limitations and tool access, without overcomplicating the prompt.

5. **Reduced redundancy and clearer structure**: The L4 prompt tightens language, reduces minor repetition, and maintains a structured, skimmable layout. This makes it easier to maintain and reason about in future levels.

Overall, L4 is not a radical departure but a cleaner, more operationally precise version of L3 that should behave almost identically in typical user interactions while handling edge cases and multimodal inputs more consistently. It remains well-suited for further iterative self-improvement if desired.