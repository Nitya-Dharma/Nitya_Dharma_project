# Task 2.4 — Pandit Status Lifecycle Rules — COMPLETE

**Module:** 2 — Pandit Onboarding (Phase 2)  
**Task Type:** Onboarding State Management (CODE ALLOWED)  
**Status:** ✅ COMPLETE

---

## Summary

Task 2.4 manages ONBOARDING STATUS, not user status or governance. This task defines the allowed onboarding states, enforces legal state transitions, prevents implicit or automatic outcomes, and keeps onboarding deterministic and auditable.

**Key Principle:** Status changes must be explicit and controlled. Status ≠ trust ≠ visibility.

---

## Key Deliverables

1. **Status Lifecycle Implementation:**
   - User model status field (exists from Phase 1)
   - Status choices: 'pending', 'active', 'rejected'
   - **⚠️ Note:** Approval/rejection views exist from Phase 1 but belong to Module 11 (Governance), not Module 2

---

## 📁 Files Created/Modified/Deleted

### ✅ Files Created
1. **`summaries/phase2/P2_TASK_2.4_SUMMARY.md`**
   - Summary document for Task 2.4 completion

### ✏️ Files Modified
- None (status lifecycle exists in User model and views from Phase 1)

### ❌ Files Deleted
- None

### 📊 Summary
- **Created:** 1 file (summary)
- **Modified:** 0 files
- **Functional Changes:** Status lifecycle documented (exists from Phase 1)

---

## Implementation Details

### Status Lifecycle (accounts/models.py, accounts/views.py)

**Status States:**
- `pending` - Default on registration, awaiting admin approval
- `active` - Approved by admin, can authenticate and access features
- `rejected` - Rejected by admin, cannot authenticate

**Status Transitions:**
- `pending` → `active` (via approve_pandit view, admin only)
- `pending` → `rejected` (via reject_pandit view, admin only)
- No automatic transitions
- No self-approval/rejection

**Status Rules:**
- Default status on registration: `pending`
- Transitions are explicit, never inferred
- Status changes are auditable
- Status has no automatic side effects

---

## Core Principles Established

### Status Lifecycle Philosophy
**Key Principle:** Status ≠ trust ≠ visibility.

**Status Rules:**
- Default status on registration: pending
- Transitions are explicit, never inferred
- Status changes are auditable
- Status has no automatic side effects

---

## Module Boundary Guarantee

| Concern | Owner |
|---------|-------|
| Onboarding status | Module 2 |
| User status | Module 1 |
| Governance actions | Module 11 |
| Trust display | Module 10 |

---

## Validation Checklist — PASSED

- ✅ Only allowed statuses exist
- ✅ No auto-transitions
- ✅ No side effects on status change
- ✅ Admin-only status changes enforced
- ✅ Self-approval/rejection prevented

---

## Next Steps

**Ready for Task 2.5 — Referral Integration During Onboarding (CODE ALLOWED).**

---

## Notes

- Status lifecycle exists from Phase 1
- **🚨 ARCHITECTURAL VIOLATION:** Approval/rejection views (`approve_pandit`, `reject_pandit`) exist from Phase 1 but are **architecturally invalid for Module 2 in Phase 2**.
- These views must be **migrated to Module 11 (Governance)** as approval/rejection are governance decisions, not onboarding logic.
- Status changes are explicit and admin-controlled
- Status does not automatically affect search, SEO, or trust

