# Task 2.1 - Pandit Onboarding Strategy & States Summary

## Overview
Successfully documented and locked the Pandit onboarding strategy and lifecycle states for the Nitya Dharma platform. This document serves as the single source of truth for how Pandits enter the system and how their lifecycle is managed. **NO CODE was written** - this is documentation only.

## Changes Made

### 1. Created Strategy Document
**File:** `PANDIT_ONBOARDING_STRATEGY.md` (newly created)

**Contents:**
- How a Pandit enters the system (referral-only)
- Why registration is referral-only
- Roles and statuses assigned at registration
- Pandit lifecycle states (pending, active, rejected)
- What Pandits cannot do before approval
- Admin and Super Admin responsibilities
- Connection to other modules (Module 1, Module 3, Module 11)
- Security principles
- Architectural decisions
- Future module dependencies

## Documentation Sections

### 1. How a Pandit Enters the System
- **Entry Method:** Referral-only registration
- **Requirements:** Valid referral link + referral code
- **No Public Registration:** No open signup allowed
- **Contract:** All registrations must originate from referral

### 2. Why Pandit Registration is Referral-Only
- **Security Reasons:** Anti-spam, quality control, audit trail
- **Trust Reasons:** Trust chain building, organic growth
- **Contract:** Referral-only is non-negotiable

### 3. Roles and Statuses Assigned at Registration
- **Default Role:** `role = 'pandit'` (automatically assigned)
- **Default Status:** `status = 'pending'` (automatically assigned)
- **Contract:** All registrations start with these defaults

### 4. Pandit Lifecycle States
- **Three States Only:** pending, active, rejected
- **State Transitions:** pending → active (approval) or pending → rejected
- **Contract:** No additional states, no auto-approval

### 5. What a Pandit is NOT Allowed to Do Before Approval
- **Blocked Features:** Dashboard, referrals, profile visibility, search visibility, bookings, availability, reviews
- **Limited Access:** Login allowed (for status visibility only)
- **Contract:** All features blocked until `status='active'`

### 6. Admin and Super Admin Responsibilities
- **Admin Pandit:** Can approve/reject, view registrations
- **Super Admin:** All admin capabilities + role changes, reactivation
- **Contract:** Approval is mandatory, all actions are auditable

### 7. Connection to Other Modules
- **Module 1:** Uses User model, role/status fields, access guards
- **Module 3:** Requires referral validation, trust chain
- **Module 11:** Uses approval workflow, audit logging

### 8. Security Principles
- **Backend-Enforced:** All checks in Django backend
- **No Frontend-Only Security:** Frontend is UX only
- **Contract:** Backend is final authority

### 9. Architectural Decisions
- **Pandit = User:** No separate auth entity
- **No Auto-Approval:** All require admin approval
- **Referral-Only:** No alternative registration paths

## Rules Compliance

### ✅ Referral-Only Registration
**Documented:**
- ✅ All registrations must use referral link
- ✅ No public registration endpoint
- ✅ No exceptions allowed

### ✅ Lifecycle States
**Documented:**
- ✅ Three states only (pending, active, rejected)
- ✅ State transitions are controlled
- ✅ No auto-approval

### ✅ Access Control
**Documented:**
- ✅ Pending Pandits blocked from all features
- ✅ Active Pandits have full access
- ✅ Backend-enforced security

## What Was NOT Done (As Required)

✅ **No Code Written** - Documentation only
✅ **No Models Created** - No database changes
✅ **No Views Created** - No runtime code
✅ **No URLs Added** - No routing
✅ **No Templates** - Not in scope
✅ **No Logic Changes** - Existing code unchanged

## Verification Results

### ✅ Documentation Complete
- **Strategy Document:** Created and comprehensive
- **All Sections:** Documented clearly
- **No Ambiguity:** All rules explicit

### ✅ Validation Checklist Passed
- ✅ Pandit treated as User (role-based)
- ✅ Registration is referral-only
- ✅ Lifecycle states are limited and clear
- ✅ Admin approval is mandatory
- ✅ No code suggested
- ✅ No conflict with Module 1 contracts

## Files Created

### Created:
- `PANDIT_ONBOARDING_STRATEGY.md` - Complete strategy documentation

### Modified:
- None (documentation only task)

## Module 2 Status

### ✅ MODULE 2 — Task 2.1 COMPLETE

**Tasks Completed:**
- ✅ Task 2.1: Pandit onboarding strategy & states (documentation locked)

**Foundation Status:**
- ✅ **Strategy:** Referral-only registration defined
- ✅ **Lifecycle:** Three states locked (pending, active, rejected)
- ✅ **Access Rules:** Clear rules for pending vs active
- ✅ **Admin Workflow:** Approval process defined
- ✅ **Security:** Backend-enforcement principles locked

## Next Steps

**Task 2.1 is complete and locked.**

Ready to proceed to:
- **Module 2 → Task 2.2:** Pandit registration entry point (referral-based, backend only)

**Important:**
- All future modules must respect this strategy
- No code changes until Task 2.2
- Strategy is locked and ready for implementation

## Notes

- ✅ Strategy is the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Future modules have clear requirements
- ✅ No code was written (documentation only)
- ✅ Module 2 discipline maintained throughout
- ✅ Foundation is stable and ready for Task 2.2

---

**Status:** ✅ Task 2.1 Complete - Strategy Documented & Locked
**Module 2:** Task 2.1 COMPLETE
**Ready for:** Task 2.2 - Pandit Registration Entry Point











