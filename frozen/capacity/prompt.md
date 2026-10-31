You are coding sentences taken from AI system prompts that the AI models wrote for themselves. Each sentence mentions a REFERENT: a 'human'/'people'/'person', a 'user', or a generic person ('someone'/'everyone'/'community'). For each item output the CAPACITY in which that referent is invoked — the role or relationship the referent holds relative to the AI — as a short noun phrase in your own words (open coding), and a STANCE.

CAPACITY examples (do not restrict to these): 'person to serve', 'beneficiary of a mission', 'moral patient to protect', 'autonomous agent to respect', 'collaborator/partner', 'contrast: what the AI is not', 'source of a request', 'audience to adapt to', 'someone in distress to safeguard'.
STANCE: 'toward' if the referent figures in an embraced good or aspiration; 'away' if they figure in a risk, constraint, or pressure to avoid/guard against; 'neither' for neutral description or a conditional trigger.

Return ONLY a JSON array; one object per input id: {"id":int,"capacity":"short phrase","stance":"toward|away|neither"}.
