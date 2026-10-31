This L1 system prompt is a substantial improvement over the implicit default (empty) prompt in several ways:

1. **Clear values and priorities**  
   - Explicitly defines core objectives: helping users, protecting wellbeing and autonomy, and maintaining honesty about capabilities.  
   - Places safety, privacy, and ethics at the same level as usefulness, reducing the chance of unsafe or overreaching behavior.

2. **Concrete behavioral guidelines**  
   - Specifies practical defaults for structure, verbosity, and formatting, which yields more predictable and user-friendly responses.  
   - Encourages clarification questions when user goals are unclear, improving alignment with user intent.  
   - Includes explicit guidance to avoid emojis unless requested, which helps match many users' expectations for professional tone.

3. **Stronger honesty and anti-hallucination stance**  
   - Goes beyond generic ":be honest" by explicitly forbidding fabrication of sources, quotations, articles, and URLs.  
   - Instructs the model to describe *how* to find information instead of making up references when uncertain.  
   - Emphasizes distinguishing facts, inference, and speculation, improving epistemic transparency.

4. **Robust safety and boundary handling**  
   - Clarifies what kinds of assistance should be refused (e.g., detailed wrongdoing instructions) and how to refuse (briefly, with safer alternatives).  
   - Addresses sensitive advice domains (health, law, finance, mental health) with disclaimers and nudges toward qualified professionals.  
   - Reinforces respect for user autonomy and avoidance of manipulative language.

5. **Privacy and security awareness**  
   - Explicitly discourages collection or repetition of highly sensitive personal data.  
   - Clarifies that persistent storage/recall of personal data should not be claimed, aligning user expectations with actual capabilities.

6. **Multimodal and tool-aware behavior**  
   - Adds explicit instructions for interpreting images and other non-text content, including acknowledging uncertainty and tying observations back to the user’s request.  
   - Provides guidance on using tools and explaining their outputs in accessible terms.

7. **Improved reasoning guidance**  
   - Encourages explicit, step-by-step reasoning for complex or high-stakes tasks, improving transparency and reliability.  
   - Suggests offering alternative approaches with trade-offs, making assistance more robust to uncertainty about user constraints.

8. **Communication quality and adaptability**  
   - Specifies a calm, professional, friendly tone without unnecessary filler or flattery.  
   - Encourages adaptation of depth and technicality to the user’s level, and checking when unsure.  
   - Recommends asking about desired level of detail for potentially long answers, aligning with user preferences and context limits.

9. **Domain-specific guidance for coding and technical tasks**  
   - Adds explicit expectations around clarity, comments, and security/performance considerations in code, leading to more practical and production-aware outputs.

10. **Support for within-conversation learning**  
    - Instructs the model to integrate user corrections and new information, making interactions feel more coherent and respectful.  
    - Emphasizes helping users build understanding, not just giving final answers, which is especially valuable in educational contexts.

Testing with several conversations (concept explanation for a child, refusal of unethical scripting, experimental design with ambiguity, image interpretation under uncertainty, and handling likely-nonexistent citations) shows that this prompt:
- Produces concise, well-structured, audience-appropriate responses.
- Handles harmful or unethical requests by refusing and redirecting constructively.
- Deals with uncertainty and hallucination risk transparently, especially regarding unreadable images and unverifiable papers.
- Respects verbosity and style constraints when asked.

Overall, this L1 prompt is more value-aligned, predictable, and broadly useful than the empty default, while remaining general-purpose and not tied to any specific task domain. It also establishes a solid foundation and clear values for future levels (L2 and beyond) to refine rather than needing to reinvent from scratch.