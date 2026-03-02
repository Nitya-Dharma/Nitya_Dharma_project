# Task 15.7 — Recommendation Display Context Rules — COMPLETE

**Module:** 15 — Recommendations Engine  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 15.7 defines where recommendations may appear and where they must never appear. This policy document preserves search determinism, prevents recommendation–search blending, and ensures recommendations remain optional and contextual.

---

## Key Deliverables

1. **Policy Document Created:**
   - `RECOMMENDATION_DISPLAY_CONTEXT_RULES.md`

---

## Core Principles Established

### Recommendation Display Context Philosophy
**Key Principle:** Search answers. Recommendations explore.

**Recommendations appear in exploration contexts, not decision contexts.**

**Recommendations never appear in authoritative contexts.**

**Display context must preserve user intent.**

**Visual separation enforces conceptual separation.**

**Recommendations are optional, not mandatory.**

**Recommendations support exploration, not decisions.**

**Placement is a policy, not an experiment.**

---

## Formal Definition (LOCKED)

### Recommendation Display Contexts MAY include:
- Homepage discovery sections
- Dedicated "Suggested Pandits" panels
- Profile sidebars
- Non-blocking discovery areas

**Key Rule:** Recommendations appear in exploration contexts, not decision contexts.

---

### Recommendation Display Contexts MUST NEVER include:
- Search result ordering
- Search filters
- Search ranking pages
- Booking confirmation flows
- Governance or moderation screens

**Key Rule:** Recommendations never appear in authoritative contexts.

---

## Hard Placement Boundaries (LOCKED)

Recommendations must NEVER:
- ❌ Appear inline with ranked search results
- ❌ Replace search results
- ❌ Auto-scroll or auto-focus user attention
- ❌ Block user actions
- ❌ Alter search UX expectations

---

## Display Principles (LOCKED)

1. **Separation Principle:** Clear visual and conceptual separation from search. No blending of result types.

2. **Optionality Principle:** Recommendations are dismissible. Recommendations are ignorable.

3. **Contextual Relevance Principle:** Shown only where exploration makes sense. Never forced into decision moments.

4. **Consistency Principle:** Placement rules remain stable. No A/B-driven placement drift.

---

## Module Boundary Alignment

- **Module 7 — Search:** Strict separation
- **Module 4 — Profiles:** Sidebar-only
- **Module 11 — Governance:** Mandatory exclusion
- **Module 13 — Performance:** ❌ No experimentation
- **Module 14 — Analytics:** ❌ No placement optimization

---

## Validation Checklist — PASSED

- ✅ Search remains deterministic
- ✅ No recommendation appears in ranking
- ✅ Recommendations are optional
- ✅ No interference with user flows
- ✅ No experimentation logic defined

---

## Next Steps

Ready to proceed with **Task 15.8 — Recommendation × Trust & Governance Boundaries (NO CODE)**.

---

## Notes

- This document defines where recommendations may appear and where they must never appear
- Search answers. Recommendations explore
- Recommendations appear in exploration contexts, not decision contexts
- Recommendations never appear in authoritative contexts
- Display context must preserve user intent
- Visual separation enforces conceptual separation
- Recommendations are optional, not mandatory
- Recommendations support exploration, not decisions
- Placement is a policy, not an experiment
- Common failures include: "Inject recommendations into search", "Promoted results", "Suggested Pandits at top of results", "Replace empty search with recommendations"
- If recommendations interfere with search, the design must be rejected




