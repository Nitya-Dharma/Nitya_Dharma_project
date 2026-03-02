# Task 11.8 — Pandit Notification Rules for Governance Actions — COMPLETE

**Module:** 11 — Governance, Moderation & Appeals  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 11.8 establishes notification rules for governance actions in Module 11 — Governance, Moderation & Appeals. This policy document defines when and how Pandits are notified of governance actions, ensuring notifications are private, neutral, and informative without implying guilt, outcomes, or discouraging appeals.

---

## Key Deliverables

1. **Policy Document Created:**
   - `PANDIT_NOTIFICATION_RULES_GOVERNANCE_ACTIONS.md`

---

## Core Principles Established

### Notification Philosophy
**Key Principle:** Notifications inform — they do not judge, warn, or coerce.

**Governance communicates facts, not conclusions.**

---

## Notification Events (LOCKED)

Pandits may be notified ONLY when:
- A report is filed against them
- A limited block is applied
- A full block is applied
- Restrictions are lifted
- An appeal decision is finalized

**Key Rule:** No silent governance actions allowed.

---

## Notification Content Rules (LOCKED)

**Notifications MAY include:**
- Action type (report / limited block / full block)
- Neutral reason category (policy reference only)
- Appeal eligibility information

**Notifications MUST NOT include:**
- ❌ Reporter identity
- ❌ Evidence details
- ❌ Speculation or assumptions
- ❌ Outcome predictions
- ❌ Threatening or warning language

---

## Visibility & Delivery Rules (LOCKED)

**Notifications must be:**
- Private (Pandit-only)
- Delivered via authenticated channels
- Logged for audit

**Notifications must NEVER be:**
- ❌ Publicly visible
- ❌ Searchable by others
- ❌ Used as trust or reputation signals

---

## Notification Principles (LOCKED)

1. **Neutral Language Principle:** No blame, no accusation, no moral framing.

2. **Transparency-with-Limits Principle:** Enough information to understand action, not enough to infer judgment.

3. **Appeal-Safety Principle:** Notification must not discourage appeals. No framing that implies finality.

---

## Module Boundary Alignment

- **Module 11 (Governance):** Sends notifications
- **Module 1 (Auth):** Ensures secure delivery
- **Module 10 (Trust Display):** ❌ No notification leakage
- **Module 7 (Search):** ❌ No impact
- **Module 15 (Recommendations):** ❌ No impact

**Key Insight:** Notifications are communication only, not signals.

---

## Validation Checklist — PASSED

- ✅ Notifications are private
- ✅ Language is neutral
- ✅ No reporter identity leaked
- ✅ Appeals clearly allowed
- ✅ No trust/search/reputation coupling

---

## Next Steps

Ready to proceed with **Task 11.9 — Appeal System Rules & Eligibility (NO CODE)**.

---

## Notes

- This document establishes notification rules for governance actions
- Pandits are notified when reports are filed, blocks are applied, restrictions are lifted, or appeal decisions are finalized
- Notifications inform — they do not judge, warn, or coerce
- Governance communicates facts, not conclusions
- No silent governance actions allowed
- Notifications are private, neutral, and must not discourage appeals
- Notifications are communication only, not signals
- Common failures include: "You violated policy X", "Further action may follow", "Your account is at risk", public notification badges
- If notifications imply guilt or outcomes, the design must be rejected




