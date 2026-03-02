# Task 2.6 - Shared Master Data Usage Contract Summary

## Overview
Successfully documented and locked the Shared Master Data Usage Contract for the Nitya Dharma platform. This provides clear rules about which fields must use master tables (cities, local areas, poojas) and which fields can be free-text (name, phone, address, experience, bio). This ensures data consistency, prevents search fragmentation, and enables SEO automation while preserving Pandit flexibility. **NO CODE was written** - this is documentation and contract locking only.

## Changes Made

### 1. Created Master Data Contract Document
**File:** `MASTER_DATA_USAGE_CONTRACT.md` (newly created)

**Contents:**
- Controlled master data fields (City, Local Areas, Poojas)
- Free-text fields (Name, Phone, Address, Experience, Bio)
- Pandit update flexibility rules
- Master data creation rules (suggestions only)
- Consistency requirements across system
- Future module requirements

**Purpose:**
- Lock contract for master data usage
- Prevent free-text data pollution
- Enable accurate search and SEO automation
- Preserve Pandit flexibility
- Ensure centralized admin control

## Rules Documented

### 1. Controlled Master Data Fields (MUST USE MASTER TABLES)

**Fields That Require Master Table Selection:**
- ✅ **City** - Single selection from master table
- ✅ **Local Areas Served** - Multi-select from master table
- ✅ **Poojas Performed** - Multi-select from master table

**Rules:**
- Must NEVER accept free-text values
- Used in registration, profile updates, search filters, SEO
- All forms/search/SEO must use same master tables
- No fallback to free-text allowed

**Why:**
- Ensures data consistency
- Prevents search fragmentation
- Enables SEO automation
- Maintains admin control

**Contract:**
- ✅ City, Local Areas, and Poojas MUST use master tables
- ✅ NO free-text values allowed for these fields
- ✅ All forms/search/SEO must use same master tables

---

### 2. Free-Text Fields (ALLOWED)

**Fields That Accept Free-Text Input:**
- ✅ **Pandit Name** - Free-text input
- ✅ **Phone Number** - Free-text/numeric input
- ✅ **Address** - Free-text input (multi-line)
- ✅ **Years of Experience** - Numeric input
- ✅ **Bio / Description** - Free-text input (multi-line)

**Rules:**
- Free-text allowed (no master table required)
- Do NOT affect search filters
- Do NOT affect master data integrity
- Used for display and contact only

**Why:**
- Pandit flexibility for personal information
- No search impact (not used in filters)
- No master data impact (no consistency requirements)

**Contract:**
- ✅ Free-text fields are allowed for personal information
- ✅ These fields do NOT affect search or master data
- ✅ No master table required for these fields

---

### 3. Pandit Update Flexibility (IMPORTANT)

**Fields Pandits Can Update:**
- ✅ City selection - Can change city
- ✅ Local areas served - Can add/remove areas
- ✅ Pooja list - Can add/remove poojas

**Update Rules:**
- Updates must always be selected from approved master tables
- Cannot add free-text values
- Can update anytime (similar to availability updates)
- Changes take effect immediately (if approved Pandit)

**Why Flexibility Matters:**
- Pandits may move to different cities
- Pandits may expand service areas
- Pandits may add new poojas to their repertoire
- Similar to availability updates (Module 6)

**Contract:**
- ✅ Pandits can update master data selections
- ✅ Updates must use approved master tables
- ✅ No free-text allowed in updates
- ✅ Flexibility preserved, data discipline enforced

---

### 4. Master Data Creation Rules

**Who Can Create:**
- ❌ **Pandits:** CANNOT create cities, local areas, or poojas
- ✅ **Pandits:** CAN suggest new entries via text input
- ✅ **Super Admin:** CAN create and approve master data

**Suggestion Flow (Conceptual):**
1. Pandit needs city/area/pooja that doesn't exist
2. Pandit submits suggestion via text input
3. Suggestion enters admin review queue
4. Super Admin reviews suggestion
5. Super Admin approves and adds to master table (or rejects)
6. Once approved, Pandit can select it from master table

**Contract:**
- ✅ Only Super Admin can create master data
- ✅ Pandits can only suggest, not create
- ✅ Suggestions require Super Admin approval
- ✅ Only approved suggestions become master data

**Note:** Suggestion workflow will be implemented in future module (likely Module 11 - Admin Governance).

---

### 5. Consistency Across System

**All Forms Must Use Same Master Tables:**
- ✅ Registration form (Task 2.2)
- ✅ Profile edit form (Module 4)
- ✅ Search filters (Module 7)
- ✅ SEO automation (Module 10)

**No Fallback to Free-Text:**
- If master data entry doesn't exist, system MUST NOT fall back to free-text
- Pandit must suggest new entry
- Super Admin reviews and approves
- Once approved, Pandit can select it

**Contract:**
- ✅ All forms/search/SEO use same master tables
- ✅ No fallback to free-text for master data fields
- ✅ Suggestions required if entry doesn't exist
- ✅ System enforces master table usage

---

## Why This Task Is Critical

### Without This Lock

**Problems:**
- ❌ Search becomes unreliable (variations in names)
- ❌ SEO pages duplicate (same entity, different names)
- ❌ Pandits create inconsistent data
- ❌ Admin loses control over data quality
- ❌ Platform cannot scale cleanly

**Example:**
- "Mumbai" vs "Bombay" vs "Mumbai City" → 3 different entries
- "Ganesh Pooja" vs "Ganpati Pooja" vs "Ganesha Puja" → 3 different entries
- Search for "Mumbai" misses "Bombay" entries
- SEO creates duplicate pages for same city

---

### With This Lock

**Benefits:**
- ✅ Platform scales cleanly
- ✅ SEO automation works correctly
- ✅ Search is accurate and reliable
- ✅ Pandits retain flexibility (can update selections)
- ✅ Admin maintains control (approves all master data)
- ✅ Data consistency across entire platform

**Example:**
- One "Mumbai" entry → all Pandits use same entry
- One "Ganesh Pooja" entry → all Pandits use same entry
- Search for "Mumbai" finds all Mumbai Pandits
- SEO creates one page per city/area/pooja

---

## Integration with Previous Tasks

### Task 2.2 (Registration)
- ✅ Registration form must use master tables for city/areas/poojas
- ✅ No free-text allowed for master data fields
- ✅ Registration respects master data contract

### Task 2.4 (Access Rules)
- ✅ Master data contract applies to Active Pandits
- ✅ Active Pandits can update master data selections
- ✅ Updates must use master tables

---

## Future Module Requirements

### Module 4: Pandit Profile
**Must Respect:**
- ✅ City selection from master table
- ✅ Local areas selection from master table
- ✅ Poojas selection from master table
- ✅ No free-text allowed for master data fields
- ✅ Pandits can update selections

### Module 7: User Search & Discovery
**Must Respect:**
- ✅ Search filters use master tables
- ✅ City filter from master table
- ✅ Local area filter from master table
- ✅ Pooja filter from master table
- ✅ No free-text search for master data fields

### Module 10: Public Trust Display / SEO
**Must Respect:**
- ✅ SEO pages generated from master table entries
- ✅ URLs use master table values
- ✅ No duplicate pages for same entity
- ✅ Consistent naming across all SEO pages

### Module 11: Admin Governance
**Must Respect:**
- ✅ Super Admin can create master data
- ✅ Super Admin can approve Pandit suggestions
- ✅ Master data management interface
- ✅ Suggestion review workflow

---

## Validation Checklist

### Controlled Fields
- ✅ City is clearly identified as master data field
- ✅ Local areas are clearly identified as master data field
- ✅ Poojas are clearly identified as master data field
- ✅ All require master table selection

### Free-Text Fields
- ✅ Free-text fields are clearly separated
- ✅ No master table required for free-text fields
- ✅ Free-text fields do not affect search

### Pandit Flexibility
- ✅ Pandits can update master data selections
- ✅ Updates must use master tables
- ✅ Flexibility is explicitly allowed

### Master Data Creation
- ✅ Pandits cannot create master data
- ✅ Pandits can suggest new entries
- ✅ Only Super Admin can approve suggestions

### Consistency
- ✅ All forms use same master tables
- ✅ Search uses same master tables
- ✅ SEO uses same master tables
- ✅ No fallback to free-text

---

## Rules Compliance

### ✅ Controlled Fields Clearly Identified
- ✅ City, Local Areas, Poojas require master tables
- ✅ No free-text allowed for master data fields
- ✅ All usage points identified

### ✅ Free-Text Fields Clearly Separated
- ✅ Name, Phone, Address, Experience, Bio are free-text
- ✅ No master table required for free-text fields
- ✅ Free-text fields do not affect search

### ✅ Pandit Flexibility Explicitly Allowed
- ✅ Pandits can update master data selections
- ✅ Updates must use master tables
- ✅ Flexibility preserved, data discipline enforced

### ✅ Master Data Creation Rules Clear
- ✅ Pandits can suggest, not create
- ✅ Only Super Admin can approve
- ✅ Suggestion workflow defined

### ✅ No Code Written
- ✅ Documentation only
- ✅ No models, migrations, views, or templates
- ✅ Policy and contract locking only

---

## Next Steps

**Task 2.6 is complete and locked.**

Ready to proceed to:
- **Module 3:** Referral & Trust Chain

**Important:**
- Master data usage contract is documented and locked
- All future modules must respect these contracts
- City, Local Areas, and Poojas MUST use master tables
- No code was written (documentation only)

---

## Notes

- ✅ Master data contract is the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Future modules have clear requirements
- ✅ No code was written (documentation only)
- ✅ Module 2 discipline maintained throughout
- ✅ Ready for Module 3 (Referral & Trust Chain)

---

**Status:** ✅ Task 2.6 Complete - Master Data Usage Contract Documented & Locked
**Module 2:** Task 2.6 COMPLETE
**Ready for:** Module 3 - Referral & Trust Chain











