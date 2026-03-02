# Task 15.6 — Recommendation Output Constraints — COMPLETE

**Module:** 15 — Recommendations Engine  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 15.6 defines how recommendation outputs may be presented and what they must never imply. This policy document ensures recommendations never appear as platform approval, users retain full decision authority, and the platform remains neutral and non-judgmental.

---

## Key Deliverables

1. **Policy Document Created:**
   - `RECOMMENDATION_OUTPUT_CONSTRAINTS.md`

---

## Core Principles Established

### Recommendation Output Philosophy
**Key Principle:** Recommendations suggest options — they never validate choices.

**Recommendations are optional, not mandatory.**

**Recommendations never replace user judgment.**

**Language and placement are as important as logic.**

**Recommendations describe, not evaluate.**

**Users retain full control.**

**Platform remains neutral.**

**Safety and governance override all output logic.**

**Presentation must not upgrade meaning.**

---

## Formal Definition (LOCKED)

### Recommendation Outputs ARE:
- Optional suggestions
- Non-binding hints
- Contextual discovery aids
- Fully ignorable UI elements

**Key Rule:** Recommendations are optional, not mandatory.

---

### Recommendation Outputs are NOT:
- Endorsements
- Certifications
- Quality guarantees
- Trust signals
- Default choices
- Replacement for user judgment

**Key Rule:** Recommendations never replace user judgment.

---

## Hard Output Constraints (LOCKED)

Recommendation outputs must NEVER:
- ❌ Use words implying approval (e.g., "verified", "best", "recommended by platform")
- ❌ Guarantee service quality or outcomes
- ❌ Imply trustworthiness or safety
- ❌ Override user filters or preferences
- ❌ Force visibility of any Pandit
- ❌ Appear inside search ranking results

---

## Output Design Principles (LOCKED)

1. **Neutral Language Principle:** Descriptive, not evaluative. No positive or negative judgment.

2. **User-Control Principle:** Users may ignore, dismiss, or bypass recommendations. No dark patterns or nudging.

3. **Non-Authoritative Principle:** Recommendations never speak on behalf of the platform. Platform neutrality is preserved.

4. **Safety-First Principle:** Governance state always applies. Blocked or restricted Pandits must not appear.

---

## Module Boundary Alignment

- **Module 7 — Search:** ❌ No insertion
- **Module 10 — Trust Display:** ❌ No implication
- **Module 11 — Governance:** Mandatory enforcement
- **Module 14 — Analytics:** ❌ No optimization
- **Module 15.1:** Output respects scope

---

## Validation Checklist — PASSED

- ✅ No endorsement language
- ✅ No implied guarantees
- ✅ User choice remains primary
- ✅ No trust or authority leakage
- ✅ No code or UI logic defined

---

## Next Steps

Ready to proceed with **Task 15.7 — Recommendation Display Context Rules (NO CODE)**.

---

## Notes

- This document defines how recommendation outputs may be presented and what they must never imply
- Recommendations suggest options — they never validate choices
- Recommendations are optional, not mandatory
- Recommendations never replace user judgment
- Language and placement are as important as logic
- Recommendations describe, not evaluate
- Users retain full control
- Platform remains neutral
- Safety and governance override all output logic
- Presentation must not upgrade meaning
- Common failures include: "Platform recommends this Pandit", "Best match for you", "Verified recommendation", "Top choice"
- If recommendations sound like approval, the design must be rejected




