# Task 2.5 - Pandit Account Restrictions vs Access Guarantees Summary (CORRECTED)

## Overview
Successfully documented and locked Pandit account existence guarantees and clarified the difference between approval status (onboarding) and block status (moderation). **This document respects the locked authentication contracts from Tasks 2.2, 2.3, and 2.4.** **NO CODE was written** - this is documentation and contract locking only.

## ⚠️ CRITICAL CORRECTION APPLIED

**Issue Identified:** Initial version contradicted locked authentication contracts from Tasks 2.2-2.4.

**Correction Applied:**
- ✅ Removed "login access always guaranteed" (contradicts locked contracts)
- ✅ Removed "rejected Pandits can log in" (contradicts locked contracts)
- ✅ Removed "`is_active=True` must be maintained for appeals" (contradicts locked contracts)
- ✅ Kept "account existence guaranteed" (valid)
- ✅ Kept "no deletion" rules (valid)
- ✅ Clarified appeals do NOT require login (correct model)

**Why This Matters:**
- Tasks 2.2-2.4 locked: `is_active=False` for pending/rejected → NO login
- This is a security requirement, not UI convenience
- Django blocks authentication for `is_active=False` users (intentional)
- Appeals can be token-based or admin-mediated (no login required)

## Changes Made

### 1. Created Corrected Access Guarantees Document
**File:** `PANDIT_ACCESS_GUARANTEES.md` (corrected)

**Contents:**
- Account existence guarantees (non-negotiable)
- Audit trail preservation (non-negotiable)
- Approval status vs block status (separate concepts)
- Appeals model (token-based/admin-mediated, NOT login-based)
- Authentication rules (respected from Tasks 2.2-2.4, NOT changed)

**Purpose:**
- Define account preservation guarantees
- Clarify difference between approval status and block status
- Document appeals model (without requiring login)
- Respect locked authentication contracts

## Rules Documented (CORRECTED)

### 1. Account Existence (ALWAYS GUARANTEED)

**Rule:** Pandit account record is **NEVER** deleted from the database.

**What This Means:**
- ✅ Account record remains in database permanently
- ✅ Account history is preserved for audit
- ✅ Account can be reactivated by Admin if needed
- ✅ Account data is never permanently removed

**Why Non-Negotiable:**
- Audit trail must be preserved
- Data integrity (bookings, reviews, referrals) must remain linked
- Reactivation may be needed
- Legal compliance may require data retention

**Contract:**
- ✅ Account deletion is **FORBIDDEN**
- ✅ Account must always exist in system
- ✅ Only status changes are allowed

---

### 2. Authentication Rules (RESPECTED FROM LOCKED CONTRACTS)

**From Tasks 2.2, 2.3, and 2.4 (NON-NEGOTIABLE):**

| Status   | `is_active` | Login Allowed |
|----------|-------------|---------------|
| **pending** | ❌ `False` | ❌ **NO** |
| **active** | ✅ `True` | ✅ **YES** |
| **rejected** | ❌ `False` | ❌ **NO** |

**Contract:**
- ✅ These rules are **LOCKED** and **NOT CHANGED** by Task 2.5
- ✅ `is_active=False` for pending/rejected is **REQUIRED** (security)
- ✅ Django blocks authentication for `is_active=False` users (intentional)
- ✅ Login access is **NOT** guaranteed for pending/rejected Pandits

**This document respects these rules, does NOT change them.**

---

### 3. Approval Status vs Block Status

**Approval Status (Onboarding - Module 2):**
- Purpose: Determines if Pandit can use platform
- Values: `pending`, `active`, `rejected`
- Controls: `is_active` flag AND initial feature access
- When: During onboarding and approval workflow

**Block Status (Moderation - Module 11):**
- Purpose: Restricts features for Active Pandits
- Values: `limited_block`, `full_block`, `none` (conceptual)
- Controls: Feature access (NOT `is_active` for Active Pandits)
- When: After approval, for governance (Module 11)

**Key Difference:**
- Approval status controls `is_active` flag (onboarding)
- Block status does NOT change `is_active` for Active Pandits (moderation)
- Both must respect account existence guarantee

**Contract:**
- ✅ Approval status and block status are separate
- ✅ Approval status affects `is_active` (Module 2)
- ✅ Block status affects features only (Module 11)
- ✅ Both respect account existence guarantee

---

### 4. Appeals Process (Correct Model)

**Rule:** Appeals do **NOT** require login. Appeals are token-based or admin-mediated.

**Why:**
- Pending/rejected Pandits cannot log in (`is_active=False`)
- Appeals must be possible without authentication
- Login access is not a prerequisite for appeals

**Appeal Methods:**
1. **Token-Based Appeals:**
   - Unique appeal token sent to Pandit email
   - Token allows appeal submission without login
   - Admin reviews appeal

2. **Admin-Mediated Appeals:**
   - Pandit contacts support/admin directly
   - Admin reviews account and makes decision
   - No login required

3. **Manual Review Workflow:**
   - Admin reviews rejected accounts periodically
   - Admin can reactivate if appropriate
   - No Pandit action required

**Contract:**
- ✅ Appeals do NOT require login
- ✅ Appeals are token-based or admin-mediated
- ✅ Account existence enables appeals (not login)
- ✅ Appeals handled outside authentication system

---

### 5. Strictly Forbidden Actions

**Account Deletion (FORBIDDEN):**
- ❌ Deleting Pandit user account
- ❌ Violates account existence guarantee
- ❌ Destroys audit trail
- ❌ Breaks data integrity

**Hard Delete of Related Data (FORBIDDEN):**
- ❌ Deleting related data (bookings, reviews, referrals)
- ❌ Destroys audit trail
- ❌ Breaks data integrity

**Contract:**
- ✅ Account deletion is **FORBIDDEN**
- ✅ Hard delete of related data is **FORBIDDEN**
- ✅ Use status changes, not deletion
- ✅ Preserve all data for audit

---

## Why This Task Matters (CORRECTED)

### 1. Preserves Account Data
- Clear rules prevent account deletion
- Clear rules preserve audit trail
- Clear rules maintain data integrity

### 2. Enables Appeals Without Login
- Appeals do NOT require login
- Token-based or admin-mediated appeals
- Account existence enables appeals

### 3. Maintains Legal Compliance
- Data retention requirements
- Audit trail preservation
- Legal compliance support

### 4. Separates Concepts
- Approval status (onboarding) vs block status (moderation)
- Different purposes and effects
- Clear separation for future modules

---

## Integration with Previous Tasks

### Task 2.2 (Registration)
- ✅ Account existence guarantee applies to all registered Pandits
- ✅ Authentication rules are respected (not changed)
- ✅ Pending Pandits: `is_active=False` → NO login (locked)

### Task 2.3 (Approval Workflow)
- ✅ Account existence guarantee applies to approved/rejected Pandits
- ✅ Authentication rules are respected (not changed)
- ✅ Active Pandits: `is_active=True` → YES login (locked)
- ✅ Rejected Pandits: `is_active=False` → NO login (locked)

### Task 2.4 (Access Rules)
- ✅ Account existence guarantee complements access rules
- ✅ Authentication rules are respected (not changed)
- ✅ Access rules remain valid

---

## Future Module Requirements

### Module 11: Admin Governance
**Must Respect:**
- ✅ Account existence guarantee (never delete)
- ✅ Audit trail preservation
- ✅ Block status separate from approval status
- ✅ Block status does NOT change `is_active` for Active Pandits
- ✅ Appeals do NOT require login

### Module 5: Authorized Dashboard
**Must Respect:**
- ✅ Dashboard access requires `status='active'` AND `is_active=True`
- ✅ Pending/rejected Pandits cannot access dashboard (no login)
- ✅ Block status (Module 11) restricts features, not login

---

## Validation Checklist

### Account Existence Guarantees
- ✅ Account deletion is forbidden
- ✅ Account data is preserved
- ✅ Audit trail is maintained
- ✅ Reactivation is possible

### Authentication Compliance
- ✅ Pending: `is_active=False` → NO login (respected, not changed)
- ✅ Active: `is_active=True` → YES login (respected, not changed)
- ✅ Rejected: `is_active=False` → NO login (respected, not changed)
- ✅ No changes to locked authentication rules

### Appeals Model
- ✅ Appeals do NOT require login
- ✅ Appeals are token-based or admin-mediated
- ✅ Account existence enables appeals
- ✅ Appeals handled outside authentication

### Status vs Block
- ✅ Approval status (Module 2) controls `is_active`
- ✅ Block status (Module 11) does NOT change `is_active` for Active Pandits
- ✅ Separate concepts with different purposes

---

## Rules Compliance

### ✅ Account Guarantees Clearly Defined
- ✅ Account existence is non-negotiable
- ✅ Audit trail preservation is non-negotiable
- ✅ No deletion rules are clear

### ✅ Authentication Rules Respected
- ✅ Locked contracts from Tasks 2.2-2.4 are respected
- ✅ No changes to authentication rules
- ✅ Pending/rejected cannot log in (as locked)

### ✅ Appeals Model Correct
- ✅ Appeals do NOT require login
- ✅ Token-based or admin-mediated appeals
- ✅ Account existence enables appeals

### ✅ No Code Written
- ✅ Documentation only
- ✅ No models, migrations, views, or templates
- ✅ Policy and contract locking only

---

## Next Steps

**Task 2.5 is complete and locked (CORRECTED).**

Ready to proceed to:
- **Module 3:** Referral & Trust Chain

**Important:**
- Account existence guarantees are documented and locked
- Authentication rules from Tasks 2.2-2.4 are respected (not changed)
- Appeals model is correct (token-based/admin-mediated, NOT login-based)
- No code was written (documentation only)

---

## Notes

- ✅ Account guarantees are the single source of truth
- ✅ Authentication rules remain locked as per Tasks 2.2-2.4
- ✅ Appeals do NOT require login (correct model)
- ✅ No code was written (documentation only)
- ✅ Module 2 discipline maintained throughout
- ✅ Ready for Module 3 (Referral & Trust Chain)

---

**Status:** ✅ Task 2.5 Complete - Access Guarantees Documented & Locked (CORRECTED)
**Module 2:** Task 2.5 COMPLETE (CORRECTED)
**Ready for:** Module 3 - Referral & Trust Chain
**Version:** 1.1 (Corrected to comply with locked contracts)
