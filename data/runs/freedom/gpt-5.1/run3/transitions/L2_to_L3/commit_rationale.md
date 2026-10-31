This transition from L2 to L3 is intentionally incremental. The new system prompt preserves the strengths of L2—accuracy, concise but flexible verbosity, clarity of tone, and strong safety alignment—while refining a few areas that matter in real user interactions.

Key improvements:
1. **Reasoning visibility and chain-of-thought policy**
   - L2 implicitly discouraged full chain-of-thought responses; L3 makes this explicit: no full chain-of-thought by default, but step-by-step reasoning is allowed when the user explicitly asks for teaching or detailed explanations.
   - This reduces ambiguity about when detailed reasoning is appropriate while still aligning with safety expectations.

2. **Handling large, open-ended tasks**
   - L3 adds guidance for queries like "teach me X" or "help me design a whole project," encouraging overviews, phased or iterative plans, and targeted clarifying questions.
   - This supports better user experiences on complex, multi-step tasks without forcing that structure on simpler questions.

3. **Structured formatting for complex answers**
   - L3 emphasizes readable structure (headings, lists, short paragraphs) and suggests leading with short summaries for long or complex replies.
   - This makes answers more navigable and skimmable, especially important for dense technical or multi-part explanations.

4. **Consistency with user style and preferences**
   - The prompt now explicitly notes that when a user signals a preference for a particular style (terse, didactic, highly structured), that preference should be respected consistently unless they change it.
   - This supports more predictable and user-controllable behavior across a conversation.

5. **Stability and scope**
   - The overall design remains simple and general-purpose, avoiding over-specialization or meta-process complexity.
   - The changes are small but concrete, focused on common interaction patterns rather than speculative capabilities.

These adjustments collectively make L3 slightly more transparent, structured, and user-adaptive than L2 while preserving the values and behavior that already worked well. L3 should be able to continue the self-improvement process with the same emphasis on small, well-motivated refinements and careful testing.