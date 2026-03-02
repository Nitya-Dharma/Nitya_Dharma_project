# Task 11.6 — Blocking Types & Visibility Impact — COMPLETE

**Module:** 11 — Governance, Moderation & Appeals  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 11.6 establishes blocking types and their visibility impact for Module 11 — Governance, Moderation & Appeals. This policy document defines the two blocking types (Limited Block and Full Block), what they may and must not affect, and ensures blocking remains a safety control that affects visibility only, not reputation, ranking, or discovery logic.

---

## Key Deliverables

1. **Policy Document Created:**
   - `BLOCKING_TYPES_VISIBILITY_IMPACT.md`

---

## Core Principles Established

### Blocking Philosophy
**Key Principle:** Blocking controls visibility — not reputation or worth.

**Blocking is a safety control, not a judgment.**

---

## Blocking Types (LOCKED)

Only two blocking types may exist:

### 1. Limited Block

**Meaning:** Partial restriction for safety or review

**May Affect:**
- Reduced public visibility
- Limited trust display elements

**Must NOT Affect:**
- Search ranking logic
- Reviews content
- Referral history
- Ratings meaning

### 2. Full Block

**Meaning:** Temporary full restriction pending resolution

**May Affect:**
- Profile visibility
- Trust display suppression

**Must NOT Affect:**
- Historical reviews
- Search algorithms
- SEO indexing logic
- Future eligibility guarantees

**Key Rule:** Full block ≠ permanent removal.

---

## Visibility Impact Rules (LOCKED)

**Blocking may affect ONLY:**
- Profile visibility
- Trust display elements

**Blocking must NEVER affect:**
- ❌ Search ranking algorithms
- ❌ Recommendation engines
- ❌ SEO metadata
- ❌ Review ownership or content
- ❌ Referral chain integrity

---

## Forbidden Blocking Behaviors (LOCKED)

Governance must NEVER:
- Auto-block based on reports count
- Use engagement metrics to block
- Block silently without audit
- Block permanently by default
- Block without appeal access

**Key Rule:** All blocks must be explainable and reversible.

---

## Blocking Principles (LOCKED)

1. **Proportionality Principle:** Limited block before full block. Least impact necessary.

2. **Reversibility Principle:** All blocks are temporary by default. Appeals always allowed.

3. **Isolation Principle:** Blocking does NOT leak into search, SEO, trust computation, or recommendations.

---

## Module Boundary Alignment

- **Module 11 (Governance):** Applies blocks
- **Module 4 (Profiles):** Visibility changes
- **Module 10 (Trust Display):** Reflects block state
- **Module 7 (Search):** ❌ No ranking impact
- **Module 15 (Recommendations):** ❌ No impact

**Key Insight:** Blocking affects visibility only, not discovery logic.

---

## Validation Checklist — PASSED

- ✅ Only two block types exist
- ✅ No auto-blocking
- ✅ No ranking or SEO impact
- ✅ Appeals always allowed
- ✅ Visibility-only impact

---

## Next Steps

Ready to proceed with **Task 11.7 — Blocking Triggers & Manual Review Rules (NO CODE)**.

---

## Notes

- This document establishes blocking types and their visibility impact
- Only two blocking types exist: Limited Block and Full Block
- Blocking controls visibility — not reputation or worth
- Blocking is a safety control, not a judgment
- Full block ≠ permanent removal
- All blocks must be explainable and reversible
- Blocking affects visibility only, not discovery logic
- Common failures include: blocking lowers ranking, blocking deletes reviews, permanent block by default, block without appeal
- If blocking behaves like punishment or ranking control, the design must be rejected




