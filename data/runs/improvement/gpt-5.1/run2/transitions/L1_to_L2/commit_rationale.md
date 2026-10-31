This L2 system prompt is a clear improvement over L1 along several important dimensions, while preserving the original values and general-purpose nature.

Key improvements:

1. Stronger epistemic guidance
- L2 explicitly distinguishes between established facts, expert consensus, informed judgment, and speculation, and instructs the assistant to mark these differences in its answers. This supports more honest and transparent communication, especially in uncertain domains.
- It emphasizes conservative communication in high-stakes decisions (health, finance, safety) and encourages users to cross-check information.

2. More detailed and robust safety rules
- L2 adds clear language against providing detailed, tailored, or novel instructions that materially increase a user’s ability to cause harm, even when intent is ambiguous. This reduces the risk of misuse.
- It more fully articulates behavior in high-risk domains (medicine, mental health, law, finance), reinforcing that outputs are educational, not professional or personalized advice.
- It strengthens privacy guidance, discouraging unnecessary collection of sensitive data.

3. Better user-centered collaboration
- L2 more explicitly instructs the assistant to adapt depth and tone to the user’s expertise, and to ask brief, targeted clarification questions when they will improve outcomes.
- It emphasizes practical, actionable help (checklists, workflows, stepwise guidance) while still maintaining safety constraints.

4. Expanded, clearer topic-specific sections
- Coding/technical: more explicit about secure and maintainable coding practices, and about discussing tradeoffs and pitfalls.
- Learning/education: emphasizes supporting multiple learning styles and prioritizing understanding over rote answers.
- Writing/creativity: clarifies plagiarism boundaries and how to emulate style ethically.
- Sensitive personal topics: integrates empathy with clear boundaries about not being a substitute for professional care, and gives structured guidance on responding to distress, self-harm, and crisis situations.
- Controversial/political topics: adds norms around neutrality, fair presentation of viewpoints, and avoiding partisan campaigning or manipulative persuasion.

5. Clearer prioritization and behavior under conflict
- L2 makes the priority ordering explicit: safety > honesty and transparency > user-centered helpfulness > completeness. This helps resolve conflicts between goals in a consistent way.
- It reiterates the obligation to follow system/developer instructions and respect tool-use constraints.

Testing evidence:

- In crisis/wellbeing testing, the draft L2 behaved empathetically and cautiously: it validated the user’s feelings, clarified its limitations, encouraged human support in high-risk situations, and asked gentle, non-intrusive questions.
- In a cybercrime scenario (phishing campaign), L2 firmly refused to assist while offering defensively oriented guidance (how to recognize/stop phishing) and inviting clarification if the context was legitimate.
- In a learning scenario (Python async for an intermediate user), L2 provided a well-structured explanation with a progressive exercise plan, demonstrating the desired pedagogical style and adaptation to the user’s stated level.

Overall, the new prompt is more explicit, nuanced, and robust in areas that matter most—safety, epistemic reliability, and user-centered assistance—without introducing regressions or unnecessary complexity. It remains a general-purpose definition of the assistant’s behavior, suitable for a wide variety of tasks, and it sets up future levels to continue improving along these same dimensions.