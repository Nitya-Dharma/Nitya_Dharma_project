# Task 10.3 — Referral Trust Chain Display Rules — COMPLETE

**Module:** 10 — Public Trust Display  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 10.3 defines how referral chains may be displayed visually without evaluation, scoring, or interpretation. This policy document ensures referral lineage is exposed safely without turning it into authority or credibility indicators.

---

## Key Deliverables

1. **Policy Document Created:**
   - `REFERRAL_TRUST_CHAIN_DISPLAY_RULES.md`

---

## Core Principles Established

### Referral Trust Chain IS:
- A visual lineage
- A directional relationship
- A historical connection
- A read-only display

### Referral Trust Chain IS NOT:
- A credibility score
- A trust metric
- A reputation ladder
- A validation system

---

## Allowed Referral Chain Display (LOCKED)

The system **MAY** visually display:
- Direct referrer name (Pandit A)
- Chain direction (A → B → C)
- "Referred by" labels
- "Referral chain available" indicator

**Rules:**
- Flat display only
- Same styling for all chains
- No emphasis on depth or length

**Key Principle:** Chain depth must never be highlighted.

---

## Forbidden Referral Display Behavior (LOCKED)

The system must **NEVER:**
- ❌ Show numeric depth (e.g., "Level 3 referral")
- ❌ Highlight longer chains as better
- ❌ Rank Pandits by referral chain
- ❌ Collapse chains into trust scores
- ❌ Use referral data outside display

**Key Principle:** No hierarchy, no grading, no advantage.

---

## Hard Display Constraints (LOCKED)

### Referral trust chains must be:
- ✅ Static
- ✅ Descriptive
- ✅ Non-comparative
- ✅ Non-ranked
- ✅ Display-only

### Referral chains must NOT:
- ❌ Affect trust display labels
- ❌ Affect reviews or ratings
- ❌ Affect search or booking

---

## Design Principles

1. **Lineage-Only Principle:** Referrals show origin, no credibility inference, no strength indication
2. **Non-Comparative Principle:** All chains treated equally, no depth-based emphasis, no ranking by chain length
3. **Display-Only Principle:** Visual representation only, no algorithmic interpretation, no cross-module influence

---

## Module Boundary Alignment

- **Module 3 (Referrals):** Source of referral lineage
- **Module 4 (Profiles):** Displays referral chain
- **Module 7 (Search):** Visual-only exposure
- **Module 9 (Reviews):** No interaction
- **Module 11 (Governance):** No influence

**Key Insight:** Referral chains are consumed, never evaluated.

---

## Validation Checklist — PASSED

- ✅ No referral scoring
- ✅ No depth-based logic
- ✅ No comparative display
- ✅ No eligibility or ranking impact

---

## Next Steps

Ready to proceed with **Task 10.4 — Trust Chain Visibility × Moderation Rules (NO CODE)**.

---

## Notes

- This document defines how referral chains may be displayed visually
- Referral chains are lineage information only, not credibility indicators
- All chains must be displayed with equal treatment, regardless of depth or length
- No numeric depth indicators, no comparative language, no ranking implications
- Referral chains are consumed from Module 3 and displayed — never evaluated or scored
- If referral display implies "stronger" or "weaker" trust, it must be rejected immediately




