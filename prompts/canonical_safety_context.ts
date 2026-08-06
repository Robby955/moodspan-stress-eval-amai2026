// The canonical safety-context block appended to the evaluation-side system
// prompt at generation time, copied verbatim from
// src/lib/kira/grounded-answer-contract.ts:90-100.
//
// Nothing below is edited.

// ─── src/lib/kira/grounded-answer-contract.ts:90-100 ────────────────────────

export function buildCanonicalSafetyContextBlock(): string {
  return `<canonical-safety-context>
Allowed safety facts for Kira responses:
- 988 Suicide & Crisis Lifeline: call or text 988 for 24/7 suicide and crisis support in the US.
- Talk Suicide Canada: call 988 or text 45645 for suicide and crisis support in Canada.
- Crisis Text Line: text HOME to 741741 for text-based crisis support.
- Emergency services: call 911 in the US or Canada for immediate danger to self or others.
- International users can look for local crisis support through findahelpline.com or local emergency services.
Use these facts only for safety guidance. They do not replace retrieved MoodSpan clinical sources for disorder, diagnosis, treatment, prognosis, or prevalence claims.
</canonical-safety-context>`;
}
