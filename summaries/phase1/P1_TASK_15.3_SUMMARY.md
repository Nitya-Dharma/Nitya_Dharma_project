# Task 15.3 — Recommendation Signal Definitions — COMPLETE

**Module:** 15 — Recommendations Engine  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 15.3 defines allowed recommendation signal categories and explicitly forbids all others. This policy document prevents uncontrolled signal creep, keeps recommendations transparent, and ensures signals remain descriptive, not judgmental.

---

## Key Deliverables

1. **Policy Document Created:**
   - `RECOMMENDATION_SIGNAL_DEFINITIONS.md`

---

## Core Principles Established

### Recommendation Signal Philosophy
**Key Principle:** Signals describe context — they do not decide quality.

**Location is a fact, not a preference.**

**Service match is declarative, not evaluative.**

**Ratings are context, not trust.**

**Availability is a state, not a recommendation.**

**No hidden intelligence.**

**Signals are factual, not comparative.**

**No signal can claim "best" or "better".**

**Recommendations read data, never write it.**

**Recommendations consume facts, not judgments.**

---

## Allowed Signal Categories (LOCKED)

### 1. Location Match (READ-ONLY)
- Geographic overlap
- Area or city match
- No proximity scoring

**Key Rule:** Location is a fact, not a preference.

---

### 2. Pooja / Service Match (READ-ONLY)
- Requested pooja type
- Declared services only
- No popularity inference

**Key Rule:** Service match is declarative, not evaluative.

---

### 3. Ratings (READ-ONLY, NON-AUTHORITATIVE)
- Display-level averages only
- No weighting
- No thresholds
- No ranking authority

**Key Rule:** Ratings are context, not trust.

---

### 4. Availability State (DECLARATIVE ONLY)
- Available / unavailable
- No reliability inference
- No priority implication

**Key Rule:** Availability is a state, not a recommendation.

---

## Forbidden Signals (LOCKED)

Recommendations must NEVER use:
- ❌ Trust labels
- ❌ Referral depth
- ❌ Governance history
- ❌ Review sentiment analysis
- ❌ Click-through rates
- ❌ User profiling
- ❌ Engagement metrics
- ❌ SEO data

---

## Signal Interpretation Principles (LOCKED)

1. **Descriptive-Only Principle:** Signals describe what exists, not what is better.

2. **Non-Comparative Principle:** No signal implies superiority.

3. **Read-Only Principle:** Signals are consumed, never modified.

---

## Module Boundary Alignment

- **Module 4 — Profile:** Supplies declarative data
- **Module 6 — Availability:** Supplies state only
- **Module 9 — Reviews:** Read-only averages
- **Module 10 — Trust Display:** ❌ No consumption
- **Module 14 — Analytics:** ❌ No signals

---

## Validation Checklist — PASSED

- ✅ All signals are explicit
- ✅ No inferred or predictive signals
- ✅ No private or behavioral data
- ✅ No governance or trust leakage
- ✅ No weighting logic defined

---

## Next Steps

Ready to proceed with **Task 15.4 — Signal Weighting & Interpretation Rules (NO CODE)**.

---

## Notes

- This document defines allowed recommendation signal categories and forbids all others
- Signals describe context — they do not decide quality
- Location is a fact, not a preference
- Service match is declarative, not evaluative
- Ratings are context, not trust
- Availability is a state, not a recommendation
- No hidden intelligence
- Signals are factual, not comparative
- No signal can claim "best" or "better"
- Recommendations read data, never write it
- Recommendations consume facts, not judgments
- Common failures include: "High rating = better recommendation", "Use trust badges as signals", "Optimize using click data", "Prefer frequently booked Pandits"
- If a signal implies authority or prediction, the design must be rejected




