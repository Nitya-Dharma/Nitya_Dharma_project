# Task 7.6 Summary — Contextual Availability Ordering Rules

**Module:** 7 — User Search & Discovery  
**Task Type:** NO CODE (Policy & Architecture)  
**Status:** ✅ COMPLETE & LOCKED

---

## 📋 Task Overview

Task 7.6 defines temporary, contextual ordering rules that apply only when users explicitly select date/time. This task allows minimal, user-requested ordering so results feel relevant without turning Search into a ranking engine.

---

## ✅ Key Deliverables

1. **Ordering Conditions (All Must Be True)**
   - User explicitly selects date and/or time
   - Availability filtering (Task 7.5) has already applied
   - Ordering is binary: Available at selected time → shown first, Not available → shown later
   - **Principle:** No other signals may influence order

2. **Ordering Characteristics**
   - **Query-scoped only:** Applies only to the current search query
   - **Temporary:** Does not persist across searches
   - **Deterministic:** Same inputs produce same ordering
   - **Explainable:** Ordering logic is transparent and simple
   - **Principle:** This is not "best first", only "currently available first"

3. **Disallowed Ordering**
   - No ranking by quantity of availability
   - No ranking by trust, reviews, experience
   - No tie-breakers using other signals
   - No remembering ordering across searches
   - No converting ordering into scores

4. **Ordering Principles**
   - **Contextual Only:** Applies only when user provides explicit date/time context
   - **Binary Ordering:** Two groups only: available first, not available later
   - **Temporary and Non-Persistent:** Applies only to current query, no memory across searches
   - **No Quality Inference:** Ordering does not imply quality or preference

5. **Relationship to Other Tasks**
   - Task 7.5: Availability filtering (binary eligibility)
   - Task 7.6: Contextual ordering (this task)
   - Task 7.10: Prohibited ranking signals
   - **Principle:** Ordering is separate from filtering and must never become ranking

---

## 🔒 Architectural Guarantees

- **Contextual Only:** Ordering applies only when user provides explicit date/time context
- **Binary Ordering:** Two groups only: available first, not available later
- **Temporary and Non-Persistent:** Applies only to current query, no memory across searches
- **No Quality Inference:** Ordering does not imply quality or preference

---

## 📄 Documentation Created

- `CONTEXTUAL_AVAILABILITY_ORDERING_RULES.md` — Complete contextual availability ordering rules

---

## ✅ Validation Status

All checklist items confirmed:
- ✅ Ordering applies only with date/time
- ✅ Availability is binary, not weighted
- ✅ No other signals influence order
- ✅ Ordering resets without context

---

## ⏭️ Next Steps

**Task 7.7** — Pooja Taxonomy Consumption & Compatibility Rules (NO CODE)

This task will define:
- How Search consumes pooja taxonomy
- What matching means conceptually
- What Search must never infer or expand
- Why explicit declaration is required
- How taxonomy ownership is preserved

---

## 🎯 Module 7 Progress

- ✅ Task 7.1 — COMPLETE & LOCKED
- ✅ Task 7.2 — COMPLETE & LOCKED
- ✅ Task 7.3 — COMPLETE & LOCKED
- ✅ Task 7.4 — COMPLETE & LOCKED
- ✅ Task 7.4.1 — COMPLETE & LOCKED
- ✅ Task 7.5 — COMPLETE & LOCKED
- ✅ Task 7.6 — COMPLETE & LOCKED
- ⏳ Task 7.7 — Pending
- ⏳ Tasks 7.8-7.16 — Pending







