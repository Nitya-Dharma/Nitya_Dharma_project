# Task 16.5 — Follow / Unfollow Rules & Limits — COMPLETE

**Module:** 16 — Pages  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 16.5 defines FOLLOWING AS A SUBSCRIPTION MECHANISM — NOT A SIGNAL. This policy document ensures Follow is simple, reversible, and non-binding, following does not influence discovery, followers do not gain power or status, and Pages cannot exploit followers for visibility.

---

## Key Deliverables

1. **Policy Document Created:**
   - `FOLLOW_UNFOLLOW_RULES_LIMITS.md`

---

## Core Principles Established

### Follow / Unfollow Philosophy
**Key Principle:** Follow = "keep me updated" — not "promote this Page."

**Following requires authentication.**

**Following is gated by account status.**

**Users are never trapped as followers.**

**Following is a user preference, not a system signal.**

**Follower count is informational, not influential.**

**Notification logic lives only in Module 17.**

**Following is isolated from discovery and ranking systems.**

---

## Follow Rules (LOCKED)

### Who MAY follow Pages:
- Logged-in end users
- Logged-in Pandits
- Logged-in Temple representatives

---

### Who MUST NEVER follow Pages:
- Guest users
- Blocked users
- Suspended accounts

---

## Unfollow Rules (LOCKED)

Unfollow is:
- Immediate
- Silent
- Reversible
- No confirmation required
- No penalties or cooldowns

---

## Follow Constraints (LOCKED)

Following must NEVER:
- Affect Page ranking
- Affect search results
- Affect recommendations
- Affect trust display
- Affect governance decisions

**Follower count is:**
- Display-only
- Non-authoritative
- Non-comparable

---

## Follow × Notifications (Boundary)

Follow enables notifications (Module 17)

**Notifications are:**
- Event-based
- Rate-limited
- Non-promotional

---

## Module Boundary Alignment

- **Module 17 — Notifications:** Follow triggers delivery
- **Module 14 — Analytics:** Follow events tracked (aggregate only)
- **Module 7 — Search:** ❌ No influence
- **Module 15 — Recommendations:** ❌ No signal

---

## Validation Checklist — PASSED

- ✅ Follow is optional & reversible
- ✅ No ranking or recommendation impact
- ✅ Follower count is display-only
- ✅ Notifications are gated & limited
- ✅ No authority gained by followers

---

## Next Steps

**Ready for Task 16.6 — Page Content Types & Posting Rules.**

---

## Notes

- This document defines follow/unfollow as a subscription mechanism, not a signal
- Follow is simple, reversible, and non-binding
- Following does not influence discovery
- Followers do not gain power or status
- Pages cannot exploit followers for visibility
- Follow = "keep me updated" — not "promote this Page"
- Following requires authentication
- Following is gated by account status
- Users are never trapped as followers
- Following is a user preference, not a system signal
- Follower count is informational, not influential
- Notification logic lives only in Module 17
- Following is isolated from discovery and ranking systems
- Common failures include: boosting Pages with more followers, "Trending Pages" logic, follower-only visibility boosts, spammy notifications
- If following influences discovery or authority, the design must be rejected



