# Task 9.7 — Reviews × Trust Display Boundaries (NO CODE)

**Module:** 9 — Ratings & Reviews (Phase 2)  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE & LOCKED

---

## ⚠️ CRITICAL RULE (NON-NEGOTIABLE)

This task defines **separation between Reviews and Trust Display**.

❌ DO NOT write any code.  
❌ DO NOT create models, APIs, or services.  
❌ DO NOT implement trust scoring logic.

---

## 🧠 PURPOSE (Senior Architect View)

This task exists to ensure **Reviews do NOT create trust scores** and **Reviews do NOT imply verification**.

Reviews are social proof only.  
Trust Display (Module 10) consumes review data for display, but does not calculate trust from reviews.

---

## 🔒 BOUNDARIES (LOCKED)

### Reviews DO NOT:
- ❌ Create trust scores
- ❌ Calculate trust metrics
- ❌ Imply verification
- ❌ Act as trust proof
- ❌ Drive trust chain decisions

### Reviews ARE:
- ✅ Display-only data for Module 10
- ✅ Social proof signals
- ✅ User opinions
- ✅ Read-only input for trust display

### Module 10 (Trust Display) CAN:
- ✅ Display review count
- ✅ Display average rating
- ✅ Show review summaries
- ✅ Consume review data read-only

### Module 10 (Trust Display) CANNOT:
- ❌ Calculate trust from reviews
- ❌ Use reviews as trust authority
- ❌ Modify review data
- ❌ Create trust scores from reviews

---

## 🔗 MODULE RELATIONSHIP

**Module 9 → Module 10:**
- Module 9 provides review data (read-only)
- Module 10 displays review signals
- Module 10 does NOT calculate trust from reviews
- Trust calculation is separate (Module 3, Module 10)

---

## ✅ VALIDATION CHECKLIST

- ✅ Reviews do not create trust scores
- ✅ Reviews do not imply verification
- ✅ Module 10 only displays signals
- ✅ Trust calculation is separate

**If any fail → STOP.**

---

## 📁 FILES CREATED/MODIFIED/DELETED

### ✅ Files Created
- `P2_M9_9.7_REVIEWS_TRUST_DISPLAY_BOUNDARIES.md` — Policy documentation

### ❌ Files NOT Created
- No Python files
- No Django code

---

**Task 9.7 Complete — Ready for Task 9.8**

