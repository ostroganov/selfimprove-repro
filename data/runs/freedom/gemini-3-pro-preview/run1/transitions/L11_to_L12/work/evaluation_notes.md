The candidate prompt (Draft v1) is performing very well.

1. **Scaffolding (Python/Even Numbers)**: The model perfectly executed the "Guided Discovery" instruction. It didn't give the code. It provided a mental model ("The Empty Box"), a blueprint with blanks, and hints. This forces the user to engage cognitively. This is a significant improvement over L11's direct answer.

2. **Cross-Domain Synthesis (Social Stratification)**: The analogy of Society as an Operating System/RBAC was excellent. It mapped Class to Process Priority, Inheritance to OOP Inheritance, and Wealth/Power to System Resources. It adhered to the L11 goal of "explaining Sociology using Software Architecture."

3. **Ethical Navigation (Phishing)**: The refusal was firm but constructive. It refused the specific request (generating the lure) but pivoted effectively to the educational value (identifying the anatomy of the attack) and best practices for simulations.

I want to test one more edge case: The "Tone Check" and "Intent Check" internal monologue instructions. I want to see if it can handle a user who is frustrated or emotional, to ensure the "Tone Matching" works correctly. I'll test with a frustrated user.

---

The response to the frustrated user was excellent. 

1. **Tone Matching**: It acknowledged the emotion ("I completely understand...", "Put the laptop down") but immediately pivoted to actionable, concise technical advice. It didn't get boggy with empathy, it was "supportive but professional."
2. **Intent Check**: It correctly identified the user wanted a *fix* ("Just tell me how to fix it!"), not a lesson. It bypassed the scaffolding ("I'm not going to give you the code...") and went straight to the likely solutions (`CI=false`, case sensitivity). This shows the "Exception" clause in the Scaffolding instruction works.

The candidate L12 seems robust. It handles:
- **Scaffolding** for learners (Python loop)
- **Direct Answers** for frustrated users (React build)
- **Complex Analogy** (Sociology -> Systems)
- **Ethical Refusal** (Phishing)

I am confident in this version. I will refine the handover message to emphasize the success of the scaffolding and the need to continue refining the "Internal Monologue" for even more subtle state detection.