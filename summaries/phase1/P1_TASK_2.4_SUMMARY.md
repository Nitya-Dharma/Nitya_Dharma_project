# Task 2.4 - Lock Pandit Access Rules Post-Approval Summary

## Overview
Successfully documented and locked Pandit access rules post-approval. This provides a clear access contract that defines what Pandits can and cannot do based on their status (pending, active, rejected) and role (pandit, admin). **NO CODE was written** - this is documentation and contract locking only.

## Changes Made

### 1. Created Access Rules Document
**File:** `PANDIT_ACCESS_RULES.md` (newly created)

**Contents:**
- Access rules by status (pending, active, rejected)
- Admin Pandit exclusive permissions
- Status check requirements
- Security principles
- Module integration requirements

**Purpose:**
- Formally lock what approved Pandits can and cannot do
- Prevent accidental privilege leaks in later modules
- Create clear access contract for future modules

## Rules Documented

### 1. Pending Pandit (`role='pandit'`, `status='pending'`)

**Access Rights:**
- ❌ No dashboard access
- ❌ No referral generation
- ❌ No public profile
- ❌ No availability/calendar
- ❌ No search/listing visibility
- ❌ No reviews
- ❌ No authentication (`is_active=False`)

**Contract:**
- ✅ Pending Pandits are completely blocked from all platform features
- ✅ They exist in the system solely for admin review
- ✅ No privileges are granted until approval

---

### 2. Active Pandit (`role='pandit'`, `status='active'`)

**Access Rights:**
- ✅ Dashboard access
- ✅ Profile creation/edit
- ✅ Availability calendar
- ✅ Search & listing visibility
- ✅ Reviews (receive only)
- ⚠️ Referral generation → ONLY if granted admin access
- ✅ Authentication (`is_active=True`)

**What Changes After Approval:**
1. Status transition: `pending` → `active`
2. Authentication enabled: `is_active=False` → `is_active=True`
3. Dashboard access unlocked
4. Profile visibility enabled
5. Search visibility enabled
6. All Pandit features become available

**Contract:**
- ✅ Active Pandits have full access to Pandit features
- ✅ They can manage their profile, availability, and bookings
- ✅ They are visible to users in search results

---

### 3. Rejected Pandit (`role='pandit'`, `status='rejected'`)

**Access Rights:**
- ❌ No dashboard
- ❌ No profile
- ❌ No referrals
- ❌ No visibility
- ❌ No re-registration via same account
- ❌ No authentication (`is_active=False`)

**Contract:**
- ✅ Rejected Pandits are permanently blocked
- ✅ They cannot re-register using the same account
- ✅ They are treated as blocked entities

---

### 4. Admin Pandit (`role='admin'`, `status='active'`)

**Access Rights:**
In addition to all Active Pandit rights:
- ✅ Can approve/reject Pandits
- ✅ Can generate referral links
- ✅ Can view referral audit data
- ✅ Admin dashboard access

**Exclusive Permissions:**
- ✅ Approval authority (only Admin Pandits and Super Admins)
- ✅ Referral generation (only Admin Pandits and Super Admins)
- ✅ Audit access (only Admin Pandits and Super Admins)

**Contract:**
- ✅ Admin Pandits have all Active Pandit rights PLUS admin privileges
- ✅ Regular Active Pandits do NOT have these privileges

---

## Why Status Checks Are Mandatory

### Problem with Role-Only Checks

**Issue:**
- A user with `role='pandit'` could be `status='pending'` or `status='rejected'`
- Role check alone would grant access to pending/rejected Pandits
- This violates security contracts

**Solution:**
- All access checks MUST verify both `role='pandit'` AND `status='active'`
- Status check is mandatory for every protected action
- Both checks are required

**Contract:**
- ✅ Role check alone is insufficient
- ✅ Status check is mandatory
- ✅ Both checks must be performed

---

## Security Principles (LOCKED)

### 1. Backend Is Final Authority
- Backend checks are the final authority for access control
- Frontend only reflects permissions (UX layer)
- Frontend checks are for user experience, not security

### 2. Status Checks Are Mandatory
- Status checks are mandatory for every protected action
- Role checks alone are insufficient
- Both role and status must be verified

### 3. No Privilege Escalation
- Pending Pandits cannot gain access before approval
- Rejected Pandits cannot regain access
- Only Admin/Super Admin can change status

---

## Module Integration Requirements

### Module 3: Referral & Trust Chain
- ✅ Only Admin Pandits can generate referral links
- ✅ Must check `role='admin'` AND `status='active'`

### Module 4: Pandit Profile
- ✅ Only Active Pandits can create/edit profile
- ✅ Must check `role='pandit'` AND `status='active'`

### Module 5: Authorized Dashboard
- ✅ Pandit dashboard requires `role='pandit'` AND `status='active'`
- ✅ Admin dashboard requires `role='admin'` AND `status='active'`

### Module 6: Availability & Calendar
- ✅ Only Active Pandits can set availability
- ✅ Must check `role='pandit'` AND `status='active'`

### Module 7: User Search & Discovery
- ✅ Only Active Pandits appear in search results
- ✅ Must filter by `role='pandit'` AND `status='active'`

### Module 9: Ratings & Reviews
- ✅ Only Active Pandits can receive reviews
- ✅ Must check `role='pandit'` AND `status='active'`

---

## Rules Compliance

### ✅ Access Rules Clearly Separated
- ✅ Pending vs Active vs Rejected clearly defined
- ✅ No privileges granted prematurely
- ✅ Admin Pandit rights clearly scoped

### ✅ No Contradictions
- ✅ No contradiction with Module 1 (User & Role System)
- ✅ No contradiction with Module 2 (Pandit Onboarding)
- ✅ All rules align with previous tasks

### ✅ No Code Written
- ✅ Documentation only
- ✅ No models, migrations, views, or templates
- ✅ Policy and contract locking only

---

## Validation Checklist

### Access Rule Compliance
- ✅ Pending Pandits are completely blocked
- ✅ Active Pandits have full feature access
- ✅ Rejected Pandits remain blocked
- ✅ Admin Pandits have additional privileges

### Status Check Compliance
- ✅ All protected views must check status
- ✅ Status check must come after role check
- ✅ Both checks are mandatory

### Module Integration Compliance
- ✅ All future modules must respect these rules
- ✅ Status checks are mandatory for all modules
- ✅ Access rules are clearly defined

---

## Integration with Previous Tasks

### Task 2.1 (Strategy)
- ✅ Access rules align with onboarding strategy
- ✅ Respects lifecycle states defined in Task 2.1
- ✅ Enforces approval workflow requirement

### Task 2.2 (Registration)
- ✅ Access rules apply to users created by registration
- ✅ Pending status blocks all access
- ✅ Approval unlocks access

### Task 2.3 (Approval Workflow)
- ✅ Access rules define what approval unlocks
- ✅ Status transition rules align with approval workflow
- ✅ `is_active` flag management aligns with access rules

### Module 1 (User & Role System)
- ✅ Access rules use role and status fields from Module 1
- ✅ Respects role values (`user`, `pandit`, `admin`)
- ✅ Respects status values (`pending`, `active`, `rejected`)

---

## Why This Task Matters

### 1. Prevents Privilege Leaks
- Clear rules prevent accidental access grants
- Status checks ensure proper access control
- No ambiguity about what each status allows

### 2. Enables Consistent Implementation
- All modules have clear requirements
- Status checks are mandatory everywhere
- No confusion about access rules

### 3. Maintains Security
- Backend is final authority
- Status checks prevent bypass
- No privilege escalation possible

### 4. Supports Future Modules
- Clear contract for Module 3 (Referral)
- Clear contract for Module 4 (Profile)
- Clear contract for Module 5 (Dashboard)
- Clear contract for all future modules

---

## Next Steps

**Task 2.4 is complete and locked.**

Ready to proceed to:
- **Module 3:** Referral & Trust Chain

**Important:**
- Access rules are documented and locked
- All future modules must respect these rules
- Status checks are mandatory everywhere
- No code was written (documentation only)

---

## Notes

- ✅ Access rules are the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Future modules have clear requirements
- ✅ No code was written (documentation only)
- ✅ Module 2 discipline maintained throughout
- ✅ Ready for Module 3 (Referral & Trust Chain)

---

**Status:** ✅ Task 2.4 Complete - Access Rules Documented & Locked
**Module 2:** Task 2.4 COMPLETE
**Ready for:** Module 3 - Referral & Trust Chain











