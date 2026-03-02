# Task 10.4 — Trust Chain Visibility × Moderation Rules — COMPLETE

**Module:** 10 — Public Trust Display  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 10.4 defines how trust-related display behaves under moderation states without judgment, inference, or explanation. This policy document ensures trust display safely aligns with moderation state without implying fault, quality, or wrongdoing.

---

## Key Deliverables

1. **Policy Document Created:**
   - `TRUST_CHAIN_VISIBILITY_MODERATION_RULES.md`

---

## Core Principles Established

### Moderation-Linked Trust Display exists to:
- Prevent misinformation
- Reflect current visibility state
- Maintain user clarity

### It must NOT:
- Judge Pandits
- Penalize Pandits
- Signal wrongdoing
- Influence eligibility

**Key Principle:** Moderation controls visibility, not reputation.

---

## Moderation States — Display Definition (LOCKED)

Trust display behavior varies **ONLY** by moderation state:

### 1️⃣ Active
- Trust signals visible
- Referral chains visible
- No warning labels

### 2️⃣ Limited-Blocked
- Trust signals partially hidden
- Clear "Limited Visibility" label
- No explanation of cause

### 3️⃣ Fully-Blocked
- Trust signals hidden
- Referral chains hidden
- "Profile Not Publicly Visible" label only

**Key Principle:** No state implies guilt or fault.

---

## Forbidden Moderation Implications (LOCKED)

Trust display must **NEVER:**
- ❌ Explain why a Pandit is blocked
- ❌ Show report counts
- ❌ Suggest wrongdoing
- ❌ Display investigation details
- ❌ Show internal governance data

**Key Principle:** Governance data is never public.

---

## Hard Visibility Rules (LOCKED)

### Moderation-driven display must be:
- ✅ Binary or descriptive
- ✅ State-driven only
- ✅ Non-judgmental
- ✅ Non-explanatory

### Must NOT:
- ❌ Leak moderation reasons
- ❌ Affect trust definitions
- ❌ Affect ratings or reviews

---

## Design Principles

1. **Neutrality Principle:** No blame or inference, no judgment language, descriptive state only
2. **Non-Explanatory Principle:** No reason disclosure, no investigation details, no report counts
3. **Isolation Principle:** Moderation logic stays in governance, trust display only reflects state, no cross-module mutation

---

## Module Boundary Alignment

- **Module 11 (Governance):** Controls moderation state
- **Module 10 (Trust Display):** Reflects visibility only
- **Module 9 (Reviews):** No mutation
- **Module 7 (Search):** No ranking change

**Key Insight:** Moderation informs visibility — nothing else.

---

## Validation Checklist — PASSED

- ✅ No guilt implication
- ✅ No reason disclosure
- ✅ No trust recalculation
- ✅ No cross-module impact

---

## Next Steps

Ready to proceed with **Task 10.5 — Reviews × Trust Display Boundaries (NO CODE)**.

---

## Notes

- This document defines how trust display changes with moderation state
- Moderation states are: Active, Limited-Blocked, Fully-Blocked
- Trust display behavior is state-mapped only — no judgment or explanation
- No moderation reasons, report counts, or investigation details may be exposed
- Governance data is never public — trust display only reflects visibility state
- Moderation controls visibility, not reputation or truth
- If moderation implies judgment or penalty, it must be rejected immediately




