# Task 4.2 — Pandit Profile Core Data Model & Ownership — COMPLETE

**Module:** 4 — Pandit Profile (Phase 2)  
**Task Type:** Architecture & Policy Lock (NO CODE)  
**Status:** ✅ COMPLETE  
**📌 Note: Existing Phase-1 model documented only; no Phase-2 code authority here.**

---

## Summary

Task 4.2 defines the core PanditProfile data contract that serves as the foundation for all profile-related functionality. This task establishes the conceptual structure of profile data, separating it from identity (User model) and defining relationships with master data.

**Key Principle:** One Pandit = One PanditProfile. Profile data is separate from identity.

**Note:** This is a NO CODE task that defines the data contract. Any existing Phase-1 model is documented here, but Phase-2 does not implement code at this stage. Actual backend implementation begins at Task 4.15.

---

## Key Deliverables

1. **PanditProfile Model:**
   - OneToOne relationship with User (role='pandit')
   - Public profile fields (display_name, about_description, experience_years, languages_spoken)
   - ManyToMany relationships to master data (cities, areas, poojas)
   - SEO template fields (placeholders only)
   - Timestamps (created_at, updated_at)

---

## 📁 Files Created/Modified/Deleted

### ✅ Files Created
1. **`summaries/phase2/P2_TASK_4.2_SUMMARY.md`**
   - Summary document for Task 4.2 completion

### ✏️ Files Modified
1. **`profiles/models.py`** (existing implementation documented)
   - `PanditProfile` model contains all required fields
   - OneToOne relationship with User
   - ManyToMany relationships to master data
   - SEO template fields (placeholders only)

### ❌ Files Deleted
- None

### 📊 Summary
- **Created:** 1 file (summary)
- **Modified:** 0 files (implementation exists from Phase 1, documented here)
- **Functional Changes:** PanditProfile model structure documented and verified

---

## Model Structure

### Identity Link:
- `user` — OneToOneField to User (role='pandit')

### Public Profile Fields:
- `display_name` — Optional display name
- `about_description` — Bio/description text
- `experience_years` — Years of experience (0-100)
- `languages_spoken` — Comma-separated languages

### Master Data Relationships:
- `cities_served` — ManyToMany to City (approved only)
- `areas_served` — ManyToMany to LocalArea (approved only)
- `poojas_performed` — ManyToMany to Pooja (approved only)

### SEO Template Fields:
- `seo_title_template` — Title template with placeholders
- `seo_description_template` — Description template with placeholders
- `seo_keywords_template` — Keywords template with placeholders

### Timestamps:
- `created_at` — Auto-created timestamp
- `updated_at` — Auto-updated timestamp

---

## Model Ownership Rules

### ✅ Model Contains:
- Profile-specific data (separate from User)
- Master data references (not duplicates)
- SEO template text (placeholders only)
- Timestamps

### ❌ Model Does NOT Contain:
- Referral tokens
- Referral usage counts
- Blocking reasons
- Moderation status
- Review ratings
- Availability slots
- Media files
- Analytics fields

**Each of these has its own module.**

---

## Validation Checklist — PASSED

- ✅ One PanditProfile per Pandit
- ✅ No duplicate User data
- ✅ M2M tables created correctly
- ✅ No business logic in model
- ✅ No default SEO values
- ✅ No blocking logic
- ✅ No referral generation logic

---

## Module Boundary Guarantee

| Concern | Owner |
|---------|-------|
| Profile data structure | Module 4 |
| Identity (User model) | Module 1 |
| Master data (City, Area, Pooja) | Module 2 |
| SEO placeholder resolution | Module 7 |
| Media storage | Future Media Module |
| Profile visibility | Module 11 |

---

## Next Steps

**Ready for Task 4.3 — Pandit Profile Media Strategy & Safety Rules (NO CODE).**

---

**Status:** ✅ COMPLETE — PanditProfile model structure documented and verified.

