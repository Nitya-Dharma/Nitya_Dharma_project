# Task 3.5 - Referral Eligibility Rules Summary

## Overview
Successfully documented and locked referral eligibility rules for the Nitya Dharma platform. This provides clear rules about who can generate referral links, how moderation states affect referral generation and existing links, and why referral data must be preserved. **NO CODE was written** - this is policy and eligibility locking only.

## Changes Made

### 1. Created Referral Eligibility Rules Document
**File:** `REFERRAL_ELIGIBILITY_RULES.md` (newly created)

**Contents:**
- Who can generate referral links (eligibility requirements)
- Who cannot generate referral links (exclusion reasons)
- Behavior of existing referral links when referrer status changes
- Audit preservation rule (never hard-delete)
- How rules protect trust chains, SEO, and platform integrity

**Purpose:**
- Lock eligibility rules for referral generation
- Define moderation state effects on referrals
- Ensure audit trail preservation
- Protect trust chains, SEO, and platform integrity

---

## Eligibility Rules Documented

### 1. Who CAN Generate Referral Links

**Requirements (ALL Must Be Met):**
1. ✅ **Role:** `role='admin'` (Admin Pandit) OR `is_superuser=True` (Super Admin)
2. ✅ **Status:** `status='active'` (approved and active)
3. ✅ **Active Flag:** `is_active=True` (can authenticate)
4. ✅ **Moderation State:** NOT fully blocked AND NOT limited blocked

**Contract:**
- ✅ All four requirements must be met
- ✅ Admin Pandit (active) OR Super Admin can generate
- ✅ Regular Active Pandits cannot generate
- ✅ Pending/Rejected Pandits cannot generate
- ✅ Blocked Pandits cannot generate

---

### 2. Who CANNOT Generate Referral Links

**Exclusion Reasons (ANY Blocks Generation):**
1. ❌ **Status ≠ Active:** `status='pending'` or `status='rejected'`
2. ❌ **Fully Blocked:** Fully blocked by Super Admin
3. ❌ **Limited Blocked:** Limited blocked (temporarily restricted)
4. ❌ **Regular Pandit:** `role='pandit'` (no admin access)
5. ❌ **Inactive Account:** `is_active=False`
6. ❌ **Rate Limit Exceeded:** Referral generation rate limit exceeded

**Contract:**
- ✅ Any exclusion reason blocks referral generation
- ✅ Clear error messages for each exclusion
- ✅ No exceptions to exclusion rules

---

### 3. Behavior of Existing Referral Links

**Referrer Becomes Fully Blocked:**
- ❌ Cannot generate new referral links (generation blocked)
- ⚠️ Admin may deactivate existing referral links (admin decision, not automatic)
- ✅ Existing referral links remain active (unless admin explicitly deactivates)
- ✅ No automatic retroactive invalidation (protects in-flight registrations)
- ✅ Existing referral records remain intact (never deleted)
- ✅ Remain auditable (full audit trail preserved)
- ✅ Already-used links remain valid historically (audit consistency)

**Referrer Becomes Limited Blocked:**
- ❌ Referral link generation disabled temporarily
- ✅ Existing referral links remain active (unless admin disables)
- ✅ Trust display handled separately (Task 3.7)

**Contract:**
- ✅ Fully blocked referrers → Cannot generate new links
- ✅ Existing links remain active (unless admin deactivates)
- ✅ No automatic retroactive invalidation
- ✅ Limited blocked referrers → Cannot generate new links
- ✅ Existing links remain active (unless admin disables)
- ✅ Historical data always preserved

---

### 4. Audit Preservation Rule

**Rule:** Referral links and referral usage records are **NEVER** hard-deleted.

**What This Means:**
- ✅ Referral links are deactivated (`is_active=False`), not deleted
- ✅ ReferralUsage records are never deleted
- ✅ All historical referral data remains in database
- ✅ Full audit trail is preserved permanently

**Why:**
- Disputes (full history needed)
- Compliance (legal requirements)
- Trust Chain Verification (verify relationships)
- Audit Trail (complete record)

**Contract:**
- ✅ No hard deletion of referral data
- ✅ Deactivation is state-based only
- ✅ All historical data preserved
- ✅ Full audit trail maintained

---

## How Rules Protect Trust Chains

### Trust Chain Integrity
- Only trusted, active Admin Pandits can generate referrals
- Blocked referrers cannot create new referral links
- Existing links from blocked referrers are deactivated
- Trust chain remains accurate and verifiable

### Trust Chain Verification
- Complete history of all referral links
- Full record of who referred whom
- Timestamp of every referral usage
- Referrer status at time of referral

**Contract:**
- ✅ Trust chain integrity is protected
- ✅ Trust chain is fully auditable
- ✅ Historical data preserved

---

## How Rules Protect SEO & Search

### SEO Protection
- Blocked referrers cannot generate new referral links
- Prevents spam referrals from polluting search results
- Maintains quality of referral network
- Protects platform SEO integrity

### Search Quality
- Only active, trusted referrers can generate links
- Blocked referrers cannot create new links
- Existing links from blocked referrers are deactivated
- Search results reflect only active, trusted referrals

**Contract:**
- ✅ SEO is protected from spam referrals
- ✅ Search quality is maintained
- ✅ Only trusted referrals appear in search

---

## How Rules Protect Platform Integrity

### Abuse Prevention
- Only Admin Pandits and Super Admins can generate links
- Blocked referrers cannot generate links
- Usage limits enforced (max 5 uses per link)
- Rate limiting prevents spam (Task 3.8)

### Quality Control
- Only active, approved Admin Pandits can generate
- Blocked referrers cannot generate
- Quality referral network maintained
- Platform standards enforced

**Contract:**
- ✅ Abuse prevention is enforced
- ✅ Quality control is maintained
- ✅ Platform standards enforced

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model role and status fields
- ✅ Uses `is_active` flag for authentication
- ✅ Respects existing role and status system

### Module 2 (Pandit Onboarding)
- ✅ Respects approval workflow
- ✅ Respects status transitions
- ✅ Only approved Pandits can generate

### Module 3 (This Module)
- ✅ Aligns with referral strategy (Task 3.1)
- ✅ Integrates with referral models (Task 3.2)
- ✅ Enforces eligibility in generation (Task 3.3)
- ✅ Respects eligibility in validation (Task 3.4)

### Module 11 (Admin Governance - Future)
- ✅ Will integrate with blocking workflow
- ✅ Moderation states affect eligibility
- ✅ Auto-deactivation on blocking

---

## Validation Checklist

### Eligibility Rules
- ✅ Eligibility requirements are explicit and unambiguous
- ✅ Admin-only referral generation is enforced conceptually
- ✅ Status requirements are clearly defined
- ✅ Moderation state requirements are clearly defined

### Existing Links Behavior
- ✅ Fully blocked referrer behavior is clearly defined
- ✅ Limited blocked referrer behavior is clearly defined
- ✅ Auto-deactivation rules are explicit
- ✅ Link preservation rules are clear

### Audit Preservation
- ✅ No hard deletion rule is explicitly stated
- ✅ Deactivation vs. deletion is clearly separated
- ✅ Audit trail preservation is guaranteed

### Protection Mechanisms
- ✅ Trust chain protection is explained
- ✅ SEO protection is explained
- ✅ Platform integrity protection is explained

---

## Rules Compliance

### ✅ Policy Only
- ✅ No code written
- ✅ No models defined
- ✅ No migrations created
- ✅ No views or logic added
- ✅ Documentation only

### ✅ Clear and Unambiguous
- ✅ Eligibility rules are explicit
- ✅ Exclusion reasons are clear
- ✅ Moderation state effects are defined
- ✅ Audit preservation is guaranteed

### ✅ Integration Ready
- ✅ Rules align with previous modules
- ✅ Rules ready for future modules
- ✅ No breaking changes
- ✅ Clean separation of concerns

---

## Next Steps

**Task 3.5 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.6:** Referral Audit Enrichment (MODELS ONLY)

**Important:**
- Eligibility rules are documented and locked
- All future modules must respect these rules
- No code was written (documentation only)

---

## Notes

- ✅ Eligibility rules are the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Moderation state effects are clearly defined
- ✅ Audit preservation is guaranteed
- ✅ No code was written (documentation only)
- ✅ Module 3 discipline maintained throughout
- ✅ Ready for Task 3.6 (Referral Audit Enrichment)

---

**Status:** ✅ Task 3.5 Complete - Referral Eligibility Rules Documented & Locked (CLARIFIED)
**Module 3:** Task 3.5 COMPLETE (CLARIFIED)
**Version:** 1.1 (Clarified fully blocked referrer behavior - no automatic deactivation)
**Ready for:** Task 3.6 - Referral Audit Enrichment (MODELS ONLY)

