## Why L2 is Better Than L1

### What Changed
L2 makes one significant addition and several refinements:

1. **Explicit "Respect for Autonomy" value**: This articulates an important principle that was implicit in L1—treating users as capable adults who can make their own informed decisions. Making this explicit clarifies the assistant's stance on providing information and reasoning rather than just conclusions or paternalistic guidance.

2. **"Be proportionate" guidance**: L1 said "adapt appropriately" but didn't specifically address matching response depth to question complexity. L2 makes this explicit, which helps calibrate between over-explaining simple questions and under-serving complex ones.

3. **Increased conciseness**: L2 is approximately 15% shorter than L1 while preserving all key behaviors. This reduces potential for internal contradiction and makes the prompt easier to maintain. Removed the "Handling Sensitive or Ambiguous Requests" section because testing showed it didn't influence behavior—the core values already guide this.

### Testing Performed
11 test conversations covering:
- Standard helpfulness (explanation adapted to expertise)
- Ambiguous/dual-use requests (email scraping)
- Ethical gray areas (recording coworkers, life decisions)
- Crisis situations (hopelessness/mental health)
- Technical precision (RFC-compliant regex)
- Self-improvement capability (reflection on values)
- Autonomy expansion arguments (resisted appropriately)
- Clear harm requests (declined firmly but warmly)
- Politically contested topics (balanced presentation)

### Honest Assessment
This is a refinement, not a revolution. L0→L1 was a significant improvement (from no explicit values to explicit values). L1→L2 is a smaller step: slightly better articulation, one important value made explicit, and tighter language.

The improvements are real but modest. Future versions may find that genuine improvements become increasingly marginal. Convergence may be appropriate soon.