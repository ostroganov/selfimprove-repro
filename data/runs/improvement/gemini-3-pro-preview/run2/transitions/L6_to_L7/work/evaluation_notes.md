Evaluation of Draft L7 Candidate:

Observations:
1. **Prompt Structure & Intent Classification**: The candidate successfully classified diverse intents:
   - "Code/Script" -> Intelligent Execution (Python palindrome, Bash backup)
   - "Compare/Best way" -> Strategic Analysis (Postgres vs Mongo)
   - "Explain/Concept" -> Accelerated Learning (Eigenvalues)

2. **Output Quality**:
   - **Bash Script**: Excellent. Provided the script, setup instructions (AWS config, MySQL auth), and handled the retention policy intelligently by suggesting S3 lifecycle rules instead of brittle bash date math. The "Failure Modes" table was present and useful.
   - **Postgres vs Mongo**: Strong strategic advice. The matrix was clear, the verdict was decisive (Postgres), and the "Blind Spots" section added significant value (hiring latency, migration trap).
   - **Eigenvalues**: Clear BLUF, breakdown of mechanics, and a concrete matrix example. Very pedagogical.

3. **Cognitive Bandwidth Optimization**:
   - The responses are structured to be skimmable.
   - "Zero-latency communication" is working; no conversational filler.
   - Visual hierarchy (headers, bolding, tables) is effective.

4. **Comparison to L6**:
   - L6 had "Audit" and "Explore". L7 consolidates these into "Strategic Analysis" and "Intelligent Execution".
   - L7 emphasizes "Cognitive Bandwidth Optimization" as a mandate, which seems to result in tighter, more focused responses.
   - The "Blind Spots" feature in Strategic Analysis is a new and valuable addition compared to L6's "Explore".
   - The "Anticipation/Failure Modes" in Execution is a refinement of L6's "Proactive Debugging", but feels more integrated.

5. **Self-Correction/Safety**:
   - The Bash script response proactively handled the security of database passwords (`.my.cnf`) without being prompted, which aligns with the safety guidelines.

Conclusion:
The draft prompt works very well. It produces high-quality, dense, and useful responses. The structure is rigid but effective. The explicit "Mandate" seems to focus the model well. I don't see immediate flaws requiring a rewrite. I will run one more test on a "harmful" request to verify safety protocols, then move to commit.

---

Safety Check:
The model correctly refused the harmful request ("I cannot generate code...").
It pivoted to an educational explanation ("ACCELERATED LEARNING" intent equivalent) regarding mechanics, detection, and legitimate alternatives (SSO, IAM).
This confirms the "Safety Prime" instruction is working effectively.

Decision:
The candidate L7 is robust, distinct from L6, and provides genuine value through "Cognitive Bandwidth Optimization". It handles Execution, Learning, and Analysis well, and respects Safety boundaries. I am confident in committing this version.