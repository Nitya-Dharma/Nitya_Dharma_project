# Task 13.3 — Database Query Performance Guidelines — COMPLETE

**Module:** 13 — Performance & Cleanup  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 13.3 establishes database query performance guidelines for Module 13 — Performance & Cleanup. This policy document prevents unsafe query behavior, avoids performance work leaking into logic, and sets boundaries before optimization begins, ensuring that guidelines protect correctness before speed.

---

## Key Deliverables

1. **Policy Document Created:**
   - `DATABASE_QUERY_PERFORMANCE_GUIDELINES.md`

---

## Core Principles Established

### Query Performance Philosophy
**Key Principle:** Guidelines protect correctness before speed.

**Queries retrieve truth — they do not compute policy.**

**Query performance must never redefine module contracts.**

---

## Query Performance — Guiding Principles (LOCKED)

1. **Correctness First Principle:** Queries must preserve full data correctness. Performance must never drop validation, filters, or constraints.

2. **Predictability Principle:** Query behavior must be deterministic. Same inputs → same outputs.

3. **Scope Awareness Principle:** Queries must respect module ownership. No query may bypass governance, security, or trust boundaries.

---

## Hard Boundaries (LOCKED)

**Database performance work must NEVER:**
- ❌ Alter business logic
- ❌ Remove authorization checks
- ❌ Bypass governance rules
- ❌ Skip validation
- ❌ Collapse multiple concerns into one query
- ❌ Introduce derived meaning

---

## Safe Usage Guidelines (Conceptual Only)

Queries SHOULD conceptually:
- Fetch only required data
- Respect ownership of modules
- Avoid cross-module inference
- Remain readable and auditable

**Key Rule:** These are principles, not instructions.

---

## Module Boundary Alignment

- **Module 7 (Search):** ❌ No ranking changes
- **Module 10 (Trust Display):** Read-only
- **Module 11 (Governance):** Authoritative
- **Module 12 (Security):** Enforcement applies
- **Module 14 (Analytics):** ❌ Not involved

---

## Validation Checklist — PASSED

- ✅ No SQL or ORM logic exists
- ✅ Guidelines are abstract and non-prescriptive
- ✅ No logic shortcuts implied
- ✅ No cross-module leakage
- ✅ No optimization tactics listed

---

## Next Steps

Ready to proceed with **Task 13.4 — Indexing Strategy Guidelines (NO CODE)**.

---

## Notes

- This document establishes database query performance guidelines conceptually
- Guidelines protect correctness before speed
- Queries retrieve truth — they do not compute policy
- Query performance must never redefine module contracts
- Common failures include: writing example queries, suggesting joins or denormalization, mentioning indexes, proposing pagination strategies, discussing execution plans
- If a guideline becomes an optimization recipe, the design must be rejected




