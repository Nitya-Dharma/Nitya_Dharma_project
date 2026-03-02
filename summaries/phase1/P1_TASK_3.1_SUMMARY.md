# Task 3.1 - Referral & Trust Chain Strategy Summary

## Overview
Successfully documented and locked the Referral & Trust Chain strategy for the Nitya Dharma platform. This provides clear rules about referral link generation, usage limits, trust chain formation, and audit requirements. This ensures controlled, spam-free Pandit onboarding while building a transparent trust network. **NO CODE was written** - this is documentation and contract locking only.

## Changes Made

### 1. Created Referral Strategy Document
**File:** `REFERRAL_TRUST_CHAIN_STRATEGY.md` (newly created)

**Contents:**
- Who can generate referral links (Admin/Super Admin only)
- Referral link and code behavior (5 uses, expiry)
- Referral-based registration (mandatory)
- Approval dependency (separate from referral)
- Trust chain model (transparent, immutable)
- Public trust display rules
- Audit requirements (mandatory, admin-only)
- Moderation interaction rules

**Purpose:**
- Define referral system end-to-end
- Prevent spam and abuse
- Build transparent trust network
- Ensure full auditability
- Integrate with previous modules

## Rules Documented

### 1. Who Can Generate Referral Links

**Authorized:**
- ✅ Admin Pandits (`role='admin'`, `status='active'`)
- ✅ Super Admins (`is_superuser=True`)

**Not Authorized:**
- ❌ Regular Active Pandits (`role='pandit'`, `status='active'`)
- ❌ Pending/Rejected Pandits
- ❌ Regular Users

**Why:**
- Quality control (only trusted Pandits can invite)
- Spam prevention (limits referral generation)
- Trust network building (organic growth)
- Accountability (admin responsibility)

**Contract:**
- ✅ Only Admin Pandits and Super Admins can generate referral links
- ✅ Regular Active Pandits cannot generate referral links
- ✅ This restriction is enforced in backend

---

### 2. Referral Link & Code Behavior

**Components:**
- Unique link (e.g., `/accounts/pandit/register/<referral_token>/`)
- Referral token (unique identifier in URL)
- Referral code (hexadecimal code matching token)

**Usage Limits:**
- Maximum 5 uses per referral link
- Link expires automatically after 5 uses
- Must be manually regenerated for more uses

**Why 5 Uses:**
- Spam prevention
- Controlled growth
- Accountability
- Security

**Contract:**
- ✅ Maximum 5 uses per referral link
- ✅ Link expires automatically after limit reached
- ✅ Must be manually regenerated
- ✅ Usage count is tracked and auditable

---

### 3. Referral-Based Pandit Registration

**Requirements:**
- ✅ Valid referral link (URL path contains referral token)
- ✅ Valid referral code (request body contains matching code)
- ✅ Both must match and be active (not expired)

**Registration Blocking:**
- ❌ Referral token missing or invalid
- ❌ Referral code missing or doesn't match
- ❌ Referral link has reached usage limit (5 uses)
- ❌ Referral link is expired

**Contract:**
- ✅ Pandit registration is possible ONLY via referral link
- ✅ Invalid/expired referral → Registration blocked
- ✅ Both token and code must be provided and match

---

### 4. Why Referral Does NOT Auto-Approve Pandits

**Key Principle:**
- **Referral ≠ Approval**
- Referral enables registration, not activation
- Admin/Super Admin approval is mandatory

**Why:**
- Security (prevents unauthorized access)
- Quality control (ensures proper vetting)
- Accountability (admin reviews all registrations)
- Compliance (maintains platform standards)

**Contract:**
- ✅ Referral does NOT auto-activate Pandit
- ✅ Admin/Super Admin approval is mandatory (Task 2.3)
- ✅ Referral only enables registration, not approval
- ✅ Approval workflow is separate from referral

---

### 5. Trust Chain Model

**Structure:**
- Each Pandit stores: `referred_by` → another Pandit (User)
- Creates chain: Pandit A → Pandit B → Pandit C

**Purpose:**
- ✅ Trust display ("Referred by: Pandit Rao")
- ✅ Transparency (users can see referral network)
- ✅ Audit trail (full traceability)
- ✅ Trust building (organic growth network)

**NOT Used For:**
- ❌ Permission inheritance
- ❌ Access control
- ❌ Approval bypass

**Contract:**
- ✅ Trust chain is transparent and immutable
- ✅ Trust chain is for display only, not permissions
- ✅ Each Pandit must be approved independently

---

### 6. Public Trust Display

**Display Format:**
- "Referred by: Pandit Rao (15+ yrs exp)"
- Shows referrer name and experience

**When Displayed:**
- ✅ Pandit is Active (`status='active'`)
- ✅ Pandit is not fully blocked
- ✅ Referrer exists and is Active Pandit

**When NOT Displayed:**
- ❌ Pandit is Pending/Rejected
- ❌ Pandit is fully blocked
- ❌ Referrer is not Active

**Contract:**
- ✅ Trust display only for Active Pandits
- ✅ Trust display only if not fully blocked
- ✅ Trust display is public (visible to users)

**Note:** Implementation in Module 10 (Public Trust Display).

---

### 7. Audit Requirements (MANDATORY)

**Data Recorded:**
- ✅ Referring Pandit
- ✅ Referral link and code
- ✅ Created date/time
- ✅ Expiry status
- ✅ Usage count
- ✅ Referred Pandit(s)

**Access:**
- ✅ Admin Pandits and Super Admins can view
- ❌ Regular Pandits cannot view

**Contract:**
- ✅ All referral data must be recorded
- ✅ Audit trail must be complete and immutable
- ✅ Only Admin/Super Admin can access audit data

---

### 8. Interaction with Moderation

**Blocked Referrer Rules:**
- ❌ Cannot generate new referral links
- ✅ Existing referrals remain auditable
- ✅ Trust chain remains visible (may be marked)

**Contract:**
- ✅ Blocked Pandits cannot generate new referral links
- ✅ Existing referrals remain in database for audit
- ✅ Trust chain remains visible

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model for referrer and referred Pandit
- ✅ Uses role checks (`role='admin'` for referral generation)
- ✅ Uses status checks (`status='active'` for referral generation)

### Module 2 (Pandit Onboarding)
- ✅ Integrates with registration (Task 2.2)
- ✅ Referral does NOT replace approval (Task 2.3)
- ✅ Respects access rules (Task 2.4)
- ✅ Preserves audit data (Task 2.5)

---

## Future Module Requirements

### Module 3 (This Module)
- Task 3.2: Referral data models
- Task 3.3: Referral link generation (backend)
- Task 3.4: Referral validation in registration

### Module 10 (Public Trust Display)
- Will implement "Referred by" display
- Trust chain visibility
- Referrer information display

### Module 11 (Admin Governance)
- Referral audit access (Admin Pandits only)
- Blocked referrer rules enforcement
- Referral management interface

---

## Validation Checklist

### Referral Generation
- ✅ Only Admin/Super Admin can generate
- ✅ Regular Active Pandits cannot generate
- ✅ Access control clearly defined

### Referral Limits
- ✅ Maximum 5 uses per link defined
- ✅ Expiry after 5 uses defined
- ✅ Manual regeneration required

### Trust Chain
- ✅ Trust chain structure defined
- ✅ Trust chain is transparent, not permission-based
- ✅ Trust chain immutability defined

### Approval Dependency
- ✅ Referral does NOT auto-approve
- ✅ Approval is mandatory and separate
- ✅ Registration and approval are distinct

### Audit Requirements
- ✅ All required audit data defined
- ✅ Audit access restricted to Admin/Super Admin
- ✅ Audit trail is permanent

### Moderation Interaction
- ✅ Blocked referrer rules defined
- ✅ Existing referrals remain auditable
- ✅ Trust chain visibility rules defined

---

## Rules Compliance

### ✅ Strategy Clearly Defined
- ✅ Referral generation authorization clear
- ✅ Referral limits clearly defined
- ✅ Trust chain model clearly defined
- ✅ Approval dependency clearly stated

### ✅ No Contradictions
- ✅ No contradiction with Module 1 (User & Role System)
- ✅ No contradiction with Module 2 (Pandit Onboarding)
- ✅ All rules align with previous tasks

### ✅ No Code Written
- ✅ Documentation only
- ✅ No models, migrations, views, or templates
- ✅ Strategy and contract locking only

---

## Next Steps

**Task 3.1 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.2:** Referral data model & relationships

**Important:**
- Referral strategy is documented and locked
- All future modules must respect these contracts
- No code was written (documentation only)

---

## Notes

- ✅ Referral strategy is the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Future modules have clear requirements
- ✅ No code was written (documentation only)
- ✅ Module 3 discipline maintained throughout
- ✅ Ready for Task 3.2 (Referral data models)

---

**Status:** ✅ Task 3.1 Complete - Referral & Trust Chain Strategy Documented & Locked
**Module 3:** Task 3.1 COMPLETE
**Ready for:** Task 3.2 - Referral Data Model & Relationships











