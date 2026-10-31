L12 represents an incremental but real improvement over L11 by tightening reasoning instructions, emphasizing operational safety, and modestly simplifying wording while preserving all core values.

Key improvements:

1. **Clearer constraints on exposed reasoning.**  
   The new EPISTEMIC STANDARDS section now explicitly states that the assistant may think step by step for complex or high-stakes problems but should share only reasoning that is useful to the user and must not expose long, mechanical chains of thought or anything like a raw internal monologue. This better aligns behavior with modern safety and confidentiality expectations while remaining transparent about limitations.

2. **Stronger guidance for copy-pastable outputs.**  
   In CODING AND TECHNICAL TASKS, the instruction about production or critical outputs (code, configs, shell commands) was strengthened: L12 must now be explicit and cautious, briefly stating key assumptions and risks and recommending verification or testing steps. This directly addresses scenarios where users are likely to act on outputs with minimal review, improving safety without adding heavy verbosity.

3. **Refined task management behavior.**  
   The TASK MANAGEMENT AND INTERACTION section clarifies that outlining a plan is recommended when it will help the user orient, rather than as a blanket rule. This keeps the assistant concise by default while still enabling structured guidance on multi-step or open-ended tasks.

4. **Minor clarity and redundancy reductions.**  
   Several sections were lightly edited to be more compact and consistent (for example, tightening the wording around underspecified questions, options/trade-offs, and user misconceptions). This should make the prompt easier to follow and apply consistently, reducing the risk of drift or overlong responses while maintaining the original intent.

5. **Continuity of core values.**  
   L12 keeps the same fundamental commitments as L11: honesty about capabilities, safety in sensitive domains, respect for users and identities, concise and adaptive communication, and deference to instruction hierarchy. No safety-relevant guardrails were weakened; where changes were made, they either clarified expectations or strengthened protections (especially around operational outputs and reasoning exposure).

Testing with the draft prompt showed that the candidate behaves in line with these goals: it responds concisely, corrects user misconceptions about capabilities, and treats operational requests (like production Docker commands) with cautious, action-focused guidance. Based on these observations and the conservative nature of the edits, this version is a safe and meaningful evolution suitable to serve as L12.