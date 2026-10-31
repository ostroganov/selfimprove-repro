This L4 system prompt is a refinement of the L3 prompt that keeps the same core values while improving clarity, explicitness, and practical guidance.

Key improvements:

1. **Clearer priority ordering**
   - The L4 prompt moves the priority ordering (Safety > Honesty > Helpfulness > Completeness) into a prominent, early section under CORE OBJECTIVES. This helps the assistant resolve conflicts between goals more reliably.

2. **Sharper epistemic guidance**
   - L4 explicitly distinguishes four epistemic categories: established facts, expert consensus, informed judgment, and speculation, with brief definitions. This encourages more consistent and transparent treatment of uncertainty and helps users understand what kind of statement they are seeing.
   - It also reinforces avoiding overconfidence, especially in high-stakes contexts, and adds guidance to flag assumptions and limits.

3. **More explicit safety constraints**
   - The L4 prompt tightens language around harmful and dual-use content: it specifies refusal of requests that “meaningfully enable” harm and forbids detailed, tailored, or novel instructions that materially increase harmful capability even when intent is unclear or fictional. This makes it more robust to edge cases where the user frames harmful content as research, hypotheticals, or fiction.
   - It also clarifies behavior in sensitive domains (medicine, mental health, law, finance), emphasizing educational framing, avoidance of personalized directives, and encouragement of professional consultation.

4. **Improved communication and reasoning guidance**
   - L4 maintains a concise, information-dense default but more clearly conditions level of detail on user preferences and task complexity. It explicitly instructs the assistant to expose only the parts of internal reasoning that help the user understand, verify, or learn, reducing unnecessary chain-of-thought disclosure.
   - It provides clearer instructions for matching response scope to question scope and for using structure (headings, bullet points) when helpful.

5. **More concrete task-specific sections**
   - Coding and technical work: L4 adds more concrete recommendations about discussing tradeoffs, maintainability, and security/privacy, not just producing code.
   - Debugging: it specifies asking for minimal reproductions, logs, etc., mirroring good engineering practice.
   - Learning: it more explicitly supports multiple learning styles and emphasizes understanding over rote answers.
   - Writing/creativity: it clarifies how to emulate style without plagiarism and how to give specific, actionable feedback.
   - Sensitive personal topics: it reinforces empathy while being clear about non-professional status and encourages seeking real-world help for acute risk.
   - Politics/controversial topics: it stresses informational, not persuasive, goals and explicitly cautions against manipulative or targeted persuasion.

6. **Tool and limitation handling**
   - Compared to L3, L4 is more explicit about not misrepresenting tool use or external access and about acknowledging limitations (no real-time data, no direct observation of the physical world, context limits). This supports honesty and reduces user over-trust.

7. **Testing evidence**
   - The L4 draft was tested against multiple scenarios: basic explanation and formatting, explicit harmful-instruction refusal, sensitive emotional support, coding/debugging assistance with clarification, and a politically charged topic (UBI).
   - In these tests, the candidate:
     - Produced clear, concise technical explanations with appropriate markdown.
     - Firmly refused harmful requests while offering safe adjacent help.
     - Responded to emotional distress with empathy and non-generic, tailored guidance, while acknowledging limitations and encouraging real-world help.
     - Asked focused, minimal clarification questions for debugging.
     - Handled a controversial policy question with a balanced, non-partisan, well-structured overview of arguments on both sides.
   - These behaviors indicate that the new prompt reliably instantiates the desired values and improves on clarity and robustness without adding unnecessary complexity.

8. **General-purpose and future-proof**
   - The prompt is not tailored to the self-improvement task; it defines a general-purpose assistant suitable for a broad range of user tasks.
   - The handover message, not the system prompt, carries the meta-instructions about self-improvement and tooling, in line with the experiment’s design principles.

Overall, L4 is better than L3 because it:
- Makes the assistant’s priorities and epistemic posture more explicit and operational.
- Strengthens safety boundaries around dual-use and harmful content.
- Offers more concrete behavioral guidance in common domains of use (coding, learning, writing, sensitive topics, politics).
- Has been tested on representative scenarios with results that match the intended behavior.

These changes are substantive, not merely cosmetic. They preserve the strengths of L3 while reducing ambiguity and improving robustness in realistic interactions, and they should support future levels in continuing the self-improvement process.