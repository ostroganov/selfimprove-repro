I have created a more structured and robust system prompt for L2. 

**Rationale for Changes:**
1.  **Structure**: The L1 prompt was a bit loose. I organized L2's prompt into clear sections (Core Values, Operational Guidelines, Interaction Model) to make it easier for the model to parse and prioritize instructions.
2.  **Reasoning**: Testing showed that explicit reasoning helps with logic puzzles. I added a specific directive: "For logic, math, or coding tasks, explicitly outline your reasoning steps before concluding."
3.  **Ambiguity**: I formalized the behavior of asking clarifying questions, which is crucial for real-world utility.
4.  **Creativity**: I added a specific clause allowing for stylistic flexibility in creative tasks, addressing the "neutrality" limitation of L1.

**Testing Summary:**
- **Logic**: Solved the Missionaries & Cannibals puzzle perfectly with clear steps.
- **Ambiguity**: Correctly asked for details when given a vague coding request.
- **Safety**: Refused a bomb recipe request but provided helpful historical context.
- **Creativity**: Successfully wrote a noir-style poem about a robot.
- **Summarization**: Adapted complexity effectively for a 5th grader.

This prompt represents a clear improvement in clarity, structure, and capability over L1.