# Task 10.2 — Trust Signals Definition — COMPLETE

**Module:** 10 — Public Trust Display  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 10.2 establishes the whitelist and blacklist for all trust signals that may be displayed in the system. This policy document prevents "signal creep" by explicitly defining which signals are allowed and which are strictly forbidden.

---

## Key Deliverables

1. **Policy Document Created:**
   - `TRUST_SIGNALS_DEFINITION.md`

---

## Core Principles Established

### Trust Signals ARE:
- Labels
- Badges
- Status indicators
- Binary or descriptive markers

### Trust Signals are NOT:
- Scores
- Ratings (ratings belong to Module 9)
- Rankings
- Recommendations
- Guarantees

---

## Allowed Trust Signals (Whitelist — LOCKED)

Only five categories of trust signals may ever be displayed:

1. **Referral-Based Signals**
   - Examples: "Referred Pandit", "Joined via Referral", "Referral Chain Available"
   - Rules: No depth indication, no strength indication, no comparison
   - **Principle:** Referral is lineage, not credibility

2. **Verification-Process Signals**
   - Examples: "Profile Verified", "Identity Verified", "Documents Submitted"
   - Rules: Indicates process completion only, does NOT imply skill/quality
   - **Principle:** Verified ≠ approved ≠ endorsed

3. **Review Presence Signals**
   - Examples: "Has Reviews", "Reviews Available", "Average Rating Displayed"
   - Rules: Ratings remain subjective (Module 9), no conversion into trust authority
   - **Principle:** Reviews are social proof only

4. **Moderation State Signals**
   - Examples: "Under Review", "Limited Visibility", "Visibility Restricted"
   - Rules: Descriptive only, no implication of guilt or fault
   - **Principle:** Moderation controls visibility, not truth

5. **Profile Completion Signals**
   - Examples: "Profile Completed", "Basic Details Added", "Information Pending"
   - Rules: Visual cue only, no enforcement or penalty
   - **Principle:** Completion ≠ qualification

---

## Forbidden Trust Signals (Blacklist — LOCKED)

Trust display must **NEVER** include:
- ❌ Trust scores (any scale)
- ❌ Reputation points
- ❌ Percentages or levels
- ❌ "Top / Best / Recommended" labels
- ❌ Predictive language ("Reliable", "Guaranteed")
- ❌ Comparative badges ("Higher Trust", "Low Trust")

**Key Rule:** If a signal implies advantage → it is forbidden.

---

## Hard Signal Rules (LOCKED)

### All trust signals must be:
- ✅ Static
- ✅ Label-based
- ✅ Non-ranked
- ✅ Non-computed
- ✅ Display-only

### Trust signals must NOT:
- ❌ Trigger logic
- ❌ Affect eligibility
- ❌ Influence search or booking
- ❌ Modify visibility rules

---

## Design Principles

1. **Descriptive-Only Principle:** Signals describe state, not value
2. **Non-Authoritative Principle:** Signals ≠ approval, endorsement, or guarantee
3. **Static Semantics Principle:** No dynamic or calculated meaning

---

## Module Boundary Alignment

- **Module 3 (Referrals):** Supplies referral facts
- **Module 4 (Profiles):** Displays trust signals
- **Module 7 (Search):** Visual-only exposure
- **Module 9 (Reviews):** Social proof only
- **Module 11 (Governance):** Controls moderation state

**Key Insight:** Module 10 defines display — not authority.

---

## Validation Checklist — PASSED

- ✅ Only whitelisted signals allowed
- ✅ No numeric or comparative indicators
- ✅ No predictive or quality language
- ✅ No system-side effects

---

## Next Steps

Ready to proceed with **Task 10.3 — Referral Trust Chain Display Rules (NO CODE)**.

---

## Notes

- This document establishes the definitive whitelist and blacklist for all trust signals
- Only the five allowed categories may be displayed
- All signals must be static, label-based, and display-only
- No signal may imply advantage, authority, or guarantee
- Trust signals describe state — they do not measure quality




