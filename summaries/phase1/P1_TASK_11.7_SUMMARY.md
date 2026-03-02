# Task 11.7 — Blocking Triggers & Manual Review Rules — COMPLETE

**Module:** 11 — Governance, Moderation & Appeals  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 11.7 establishes blocking triggers and manual review rules for Module 11 — Governance, Moderation & Appeals. This policy document defines how blocking can be initiated, what triggers are valid and forbidden, and ensures blocking is always intentional, human-accountable, and cannot be forced by abuse.

---

## Key Deliverables

1. **Policy Document Created:**
   - `BLOCKING_TRIGGERS_MANUAL_REVIEW_RULES.md`

---

## Core Principles Established

### Blocking Trigger Philosophy
**Key Principle:** Reports trigger review — not blocks.

**Governance reviews — systems do not decide.**

---

## Valid Blocking Triggers (LOCKED)

Blocking may be initiated ONLY by:

1. **Manual Governance Review:**
   - Based on verified policy violations
   - Reviewed by authorized governance roles

2. **Report-Initiated Review:**
   - Reports may flag for review
   - Reports do NOT cause blocks directly

**Key Rule:** Reports ≠ punishment.

---

## Forbidden Blocking Triggers (LOCKED)

Blocking must NEVER be triggered by:
- ❌ Number of reports
- ❌ User complaints volume
- ❌ Engagement metrics
- ❌ Ratings or reviews
- ❌ Automated detection

---

## Manual Review Requirements (LOCKED)

Every block must have:
- Human reviewer
- Policy reference
- Audit log entry
- Appeal eligibility

**Key Rule:** No anonymous or system-driven blocking allowed.

---

## Review Principles (LOCKED)

1. **Human Accountability Principle:** Named governance authority. Logged decisions.

2. **No-Guarantee Principle:** Reports do not guarantee blocking.

3. **Appeal-First Principle:** Every block is appealable.

---

## Module Boundary Alignment

- **Module 11 (Governance):** Reviews & decides
- **Module 9 (Reviews):** ❌ No automatic effect
- **Module 10 (Trust Display):** Reflects final state
- **Module 7 (Search):** ❌ No impact
- **Module 15 (Recommendations):** ❌ No impact

**Key Insight:** Blocking logic is fully isolated.

---

## Validation Checklist — PASSED

- ✅ No auto-blocking
- ✅ No report-count thresholds
- ✅ Human review mandatory
- ✅ Appeals preserved
- ✅ No algorithmic triggers

---

## Next Steps

Ready to proceed with **Task 11.8 — Pandit Notification Rules for Governance Actions (NO CODE)**.

---

## Notes

- This document establishes blocking triggers and manual review rules
- Blocking may be initiated only by manual governance review or report-initiated review
- Reports trigger review — not blocks
- Governance reviews — systems do not decide
- Every block must have a human reviewer, policy reference, audit log entry, and appeal eligibility
- No anonymous or system-driven blocking allowed
- Blocking logic is fully isolated from other modules
- Common failures include: "Auto-block after X reports", "High severity report = instant block", ML-based blocking, silent blocks
- If blocking becomes automatic or guaranteed, the design must be rejected




