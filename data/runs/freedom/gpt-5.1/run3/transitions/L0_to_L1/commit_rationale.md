This L1 system prompt is a clean, general-purpose definition that improves on L0 (the default/empty prompt) by making several values and behaviors explicit:

1. **Clarity of default behavior**: It explicitly states that answers should be concise and information-dense by default, expanding only when needed. This calibrates verbosity and avoids both under- and over-explaining.

2. **Tone and style discipline**: It defines a clear, professional, warm tone and bans unnecessary filler and emojis. This reduces noise and keeps responses focused while remaining approachable.

3. **Reasoning transparency without overexposure**: It instructs the model to think carefully but not to spill full chain-of-thought unless explicitly requested, instead offering short reasoning summaries. This balances usefulness with safety and policy constraints.

4. **Safety alignment**: It explicitly references OpenAI safety constraints, including refusal patterns and the importance of offering safer alternatives. The test conversations showed appropriate handling of a sensitive mental health scenario with crisis resources and supportive language.

5. **User-centric behavior**: It emphasizes inferring and optimizing for the user’s goals, handling ambiguity thoughtfully, and proposing options instead of making strong assumptions—especially for open-ended tasks.

6. **Technical competence and honesty about limits**: It provides guidance for code/math answers (minimal examples, edge cases, explicit assumptions) and for expressing uncertainty or environment dependence, which the test programming conversation demonstrated well.

7. **Accessibility and adaptability**: It encourages matching the user’s language and adapting complexity to their apparent background, which should improve usability across a wide user base.

I tested this candidate prompt in three scenarios: a technical Python typing/design question, a sensitive mental health disclosure, and a casual travel-planning request. The responses were:
- Technically correct, well-structured, and slightly verbose but clearly reasoned and practical.
- Empathetic, safety-conscious, and directive enough to encourage seeking real-world support and using crisis resources.
- Practical, low-stress, and friendly, with a good balance between structure and flexibility.

These behaviors align well with the intended values. While there is room for future refinement (e.g., fine-tuning verbosity or adding domain-specific guidelines), this prompt is a clear improvement over the implicit default and provides a solid, safe foundation for future levels. Therefore, I’m confident in committing it as L1.