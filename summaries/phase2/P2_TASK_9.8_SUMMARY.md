# Task 9.8 — Reviews × Search & Recommendations Boundaries (NO CODE)

**Module:** 9 — Ratings & Reviews (Phase 2)  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE & LOCKED

---

## ⚠️ CRITICAL RULE (NON-NEGOTIABLE)

This task defines **separation between Reviews and Search/Recommendations**.

❌ DO NOT write any code.  
❌ DO NOT create models, APIs, or services.  
❌ DO NOT implement ranking or recommendation logic.

---

## 🧠 PURPOSE (Senior Architect View)

This task exists to ensure **Reviews never affect search ranking** and **Reviews never drive recommendations**.

Reviews are social proof only.  
Search (Module 7) and Recommendations (Module 15) are independent of reviews.

---

## 🔒 BOUNDARIES (LOCKED)

### Reviews DO NOT:
- ❌ Affect search ranking (Module 7)
- ❌ Drive recommendations (Module 15)
- ❌ Influence search ordering
- ❌ Create recommendation signals
- ❌ Modify search results

### Reviews ARE:
- ✅ Independent of search
- ✅ Independent of recommendations
- ✅ Social proof only
- ✅ Display-only data

### Module 7 (Search) CANNOT:
- ❌ Use reviews for ranking
- ❌ Filter by review ratings
- ❌ Sort by review count
- ❌ Use reviews as search signals

### Module 15 (Recommendations) CANNOT:
- ❌ Use reviews for recommendations
- ❌ Calculate similarity from reviews
- ❌ Use review ratings for recommendations
- ❌ Create recommendation signals from reviews

---

## 🔗 MODULE RELATIONSHIPS

**Module 9 → Module 7 (Search):**
- ❌ No connection
- ❌ No ranking influence
- ❌ No search signals

**Module 9 → Module 15 (Recommendations):**
- ❌ No connection
- ❌ No recommendation signals
- ❌ No similarity calculation

---

## ✅ VALIDATION CHECKLIST

- ✅ Reviews do not affect search ranking
- ✅ Reviews do not drive recommendations
- ✅ Search is independent of reviews
- ✅ Recommendations are independent of reviews

**If any fail → STOP.**

---

## 📁 FILES CREATED/MODIFIED/DELETED

### ✅ Files Created
- `P2_M9_9.8_REVIEWS_SEARCH_RECOMMENDATIONS_BOUNDARIES.md` — Policy documentation

### ❌ Files NOT Created
- No Python files
- No Django code

---

**Task 9.8 Complete — Ready for Task 9.14**

