# Task 13.11 — Soft Delete vs Hard Delete Rules — COMPLETE

**Module:** 13 — Performance & Cleanup  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 13.11 establishes soft delete vs hard delete rules for Module 13 — Performance & Cleanup. This policy document prevents irreversible loss of platform truth, ensures deletion is a governance decision (not a performance shortcut), and guarantees that "deleted" data remains recoverable when it represents authority.

---

## Key Deliverables

1. **Policy Document Created:**
   - `SOFT_DELETE_HARD_DELETE_RULES.md`

---

## Core Principles Established

### Deletion Philosophy
**Key Principle:** Deletion is a visibility change, not truth erasure.

**Soft delete is the default for all authoritative records.**

**Hard delete is FORBIDDEN for authoritative data.**

**Authoritative data is permanent unless explicitly governed.**

**No performance gain justifies truth loss.**

---

## Formal Definition (LOCKED)

### Soft Delete (REQUIRED for Authoritative Data)
Soft delete means:
- Data remains in storage
- Visibility is hidden from normal queries
- Recovery is possible
- Auditability is preserved

**Key Rule:** Soft delete is the default for all authoritative records.

---

### Hard Delete (FORBIDDEN for Authoritative Data)
Hard delete means:
- Data is permanently removed from storage
- Recovery is impossible
- Audit trail is broken
- Truth is destroyed

**Key Rule:** Hard delete is FORBIDDEN for authoritative data.

---

## Hard Delete Rules (LOCKED)

### Hard Delete MAY ONLY be used for:
- Operational residue (temporary logs, debug artifacts)
- Non-authoritative cache entries
- System-generated temp records

**Key Rule:** Hard delete is ONLY for data that never defined truth.

---

### Hard Delete MUST NEVER be used for:
- Reviews
- Referrals & trust chains
- Governance actions
- Appeals & audit logs
- Booking records
- Availability history
- User-generated content
- Pandit profiles
- User accounts (unless legally required)

**Key Rule:** Authoritative data must NEVER be hard deleted.

---

## Soft Delete Principles (LOCKED)

1. **Truth Preservation Principle:** Soft delete hides visibility, not truth.

2. **Reversibility Principle:** Soft-deleted data can be restored.

3. **Auditability Principle:** Soft delete preserves audit trail.

4. **Governance Authority Principle:** Only governance can authorize hard delete of authoritative data.

---

## Hard Delete Prohibitions (LOCKED)

**Hard delete must NEVER:**
- ❌ Be used for user-visible data
- ❌ Remove auditability
- ❌ Break referential integrity
- ❌ Be justified as "performance optimization"
- ❌ Replace governance moderation

---

## Module Boundary Alignment

- **Module 3 (Referrals):** ❌ No hard delete
- **Module 9 (Reviews):** ❌ Soft delete only
- **Module 11 (Governance):** ❌ No audit removal
- **Module 12 (Security):** ❌ No incident loss
- **Module 8 (Booking Intent):** ❌ Soft delete only

---

## Validation Checklist — PASSED

- ✅ Soft delete is default for authoritative data
- ✅ Hard delete is forbidden for authoritative data
- ✅ No deletion flags or fields defined
- ✅ No cascade rules specified
- ✅ No implementation detail present

---

## Next Steps

Ready to proceed with **Task 13.12 — Data Archival vs Deletion Policy (NO CODE)**.

---

## Notes

- This document establishes soft delete vs hard delete rules
- Deletion is a visibility change, not truth erasure
- Soft delete is the default for all authoritative records
- Hard delete is FORBIDDEN for authoritative data
- Authoritative data is permanent unless explicitly governed
- No performance gain justifies truth loss
- Common failures include: "Hard delete old reviews", "Cascade delete referrals", "Permanently remove blocked users", "Delete expired booking intents", "Performance-based hard delete"
- If deletion removes authoritative truth, the design must be rejected




