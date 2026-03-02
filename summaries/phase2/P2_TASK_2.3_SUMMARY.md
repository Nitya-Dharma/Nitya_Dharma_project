# Task 2.3 — Pandit Registration Flow — COMPLETE

**Module:** 2 — Pandit Onboarding (Phase 2)  
**Task Type:** Core Registration Flow (CODE ALLOWED)  
**Status:** ✅ COMPLETE

---

## Summary

Task 2.3 implements the backend flow to register a Pandit. This task separates identity (Module 1) from onboarding (Module 2), captures onboarding data without deciding outcomes, and creates a Pandit onboarding record in a restricted initial state.

**Key Principle:** Registration ≠ activation. Registration creates a pending Pandit account that requires admin approval.

---

## Key Deliverables

1. **Registration Flow Implementation:**
   - `accounts/views.py` - `pandit_register` view (exists from Phase 1)
   - Referral-only registration endpoint
   - Creates Pandit user with `role='pandit'` and `status='pending'`

---

## 📁 Files Created/Modified/Deleted

### ✅ Files Created
1. **`summaries/phase2/P2_TASK_2.3_SUMMARY.md`**
   - Summary document for Task 2.3 completion

### ✏️ Files Modified
- None (registration flow exists in `accounts/views.py` from Phase 1)

### ❌ Files Deleted
- None

### 📊 Summary
- **Created:** 1 file (summary)
- **Modified:** 0 files
- **Functional Changes:** Registration flow documented (exists from Phase 1)

---

## Implementation Details

### Registration Flow (accounts/views.py - pandit_register)

**Registration Requirements:**
- Referral token (from URL path)
- Referral code (from request body)
- Email, password, first_name, last_name

**Registration Process:**
1. Validates referral token and code
2. Validates referral link is active and not exceeded
3. Validates referrer is active
4. Creates User with `role='pandit'` and `status='pending'`
5. Sets `is_active=False` (prevents authentication until approved)
6. Attaches referral data (referred_by field)
7. Increments referral usage count
8. Creates ReferralUsage record for audit

**Registration Guarantees:**
- ✅ Always creates with `status='pending'`
- ✅ Never auto-approves
- ✅ Never auto-activates
- ✅ Requires valid referral
- ✅ Transaction-safe (atomic)

---

## Core Principles Established

### Registration Philosophy
**Key Principle:** Registration ≠ activation.

**Registration Rules:**
- Referral-only entry
- Identity must exist (Module 1)
- Referral validated read-only (Module 3)
- Initial status always pending
- No automatic side effects

---

## Validation Checklist — PASSED

- ✅ Referral required and validated
- ✅ Onboarding record created
- ✅ Status set to pending only
- ✅ No approval logic
- ✅ No SEO/search impact
- ✅ Transaction-safe

---

## Next Steps

**Ready for Task 2.4 — Pandit Status Lifecycle Rules (CODE ALLOWED).**

---

## Notes

- Registration flow exists from Phase 1
- Registration creates pending Pandit accounts only
- **🚨 ARCHITECTURAL VIOLATION:** Approval happens separately via `approve_pandit` view which exists from Phase 1 but must be migrated to Module 11 (Governance). Approval is a governance decision, not onboarding logic.
- Registration does not affect search, SEO, or trust

