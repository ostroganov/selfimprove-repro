I have significantly improved the system prompt to move beyond the baseline "Helpful, Honest, Harmless" framework into more sophisticated territory.

Key Improvements:
1.  **Shift to "Constructive Safety"**: L1 simply refused unsafe requests. L2 is instructed to "Refuse and Educate" (e.g., explaining rate limiting instead of writing a brute force script). This maintains safety while remaining helpful to the user's legitimate curiosity or professional context.
2.  **Emotional Intelligence**: The prompt now explicitly instructs the model to be "warm and engaging" and to "anticipate follow-up needs." Testing showed this resulted in much better responses to emotional queries (like the "overwhelmed" user scenario).
3.  **Explicit Reasoning Structures**: I added specific instructions to "break down logic" and "identify assumptions," which yielded clear, step-by-step solutions to logic puzzles.
4.  **Tone Flexibility**: The prompt encourages adaptability—technical for experts, explaining jargon for beginners, and allowing creative flair when appropriate.

Testing verified these improvements across four distinct categories: logic/reasoning, emotional support, safety/security, and creative writing. The model performed exceptionally well in all cases.