# Task 6.2 - Availability Data Model & Ownership Rules Summary

## Overview
Successfully created the Availability data model following the minimal, extensible design that is booking-agnostic, payment-agnostic, and KPI-agnostic. This is a **MODELS ONLY** task - no views, serializers, APIs, or business logic.

---

## Task Type
**MODELS ONLY** - Data Structure Only

---

## Changes Made

### 1. Created Availability App
- **Command:** `python manage.py startapp availability`
- **Location:** `availability/` directory at project root
- **Status:** App created with default Django structure

### 2. Created Availability Model
**File:** `availability/models.py`

**Model Details:**
- **Model Name:** `Availability`
- **Ownership:** One Pandit → Many Availability entries
- **Base Design:** Booking-agnostic, payment-agnostic, KPI-agnostic

**Key Features:**

#### Ownership Field
- `pandit` (ForeignKey to User)
  - Links availability to Pandit
  - CASCADE on delete
  - **NOTE:** Role enforcement (role="pandit") is handled at service/permission layer, not at database level. This ForeignKey does not enforce role constraints.

#### Temporal Fields
- `day_of_week` (IntegerField, choices, nullable)
  - For recurring availability (0=Monday, 6=Sunday)
  - Optional if using specific_date
  
- `specific_date` (DateField, nullable)
  - For one-off availability
  - Optional if using day_of_week
  
- `start_time` (TimeField, required)
  - Start time of availability window
  
- `end_time` (TimeField, required)
  - End time of availability window
  
- `is_recurring` (BooleanField, default=True)
  - Descriptive field: True if using day_of_week (recurring), False if using specific_date (one-off)
  - This is descriptive only and may be derived in future refactoring

#### Contextual Fields (from Module 2 - Master Data)
- `city` (ForeignKey to City, required)
  - City where availability applies
  - PROTECT on delete (master data protection)
  
- `area` (ForeignKey to LocalArea, optional)
  - Local area where availability applies
  - PROTECT on delete
  
- `pooja` (ForeignKey to Pooja, optional)
  - Pooja type for which availability applies
  - PROTECT on delete

#### State Fields (Descriptive Only)
- `is_active` (BooleanField, default=True)
  - Descriptive only, does not enforce availability
  
- `created_at` (DateTimeField, auto_now_add)
  - Creation timestamp
  
- `updated_at` (DateTimeField, auto_now)
  - Last update timestamp

### 3. Model Validation
- **`clean()` method:**
  - Provided for Django admin and forms only
  - NOT runtime enforcement logic
  - Ensures either `day_of_week` OR `specific_date` is set, not both
  - Validates time range (end_time > start_time)
  - Actual validation enforcement happens at service/permission layer (Task 6.3+)
  
- **No `save()` override:**
  - MODELS ONLY principle: no enforcement logic in model
  - Validation enforcement deferred to service layer

### 4. Model Meta Configuration
- **Database table:** `availability_availability`
- **Ordering:** By pandit, day_of_week/specific_date, start_time
- **Indexes:**
  - `['pandit', 'is_active']` - For filtering by Pandit
  - `['city', 'is_active']` - For filtering by city
  - `['day_of_week', 'is_active']` - For recurring availability queries
  - `['specific_date', 'is_active']` - For date-specific queries

### 5. Updated Settings
**File:** `nityadharma/settings/base.py`

**Changes:**
- Added `'availability'` to `INSTALLED_APPS`

**Before:**
```python
INSTALLED_APPS = [
    # ... Django apps ...
    'core',
    'accounts',
    'referrals',
    'masterdata',
    'profiles',
]
```

**After:**
```python
INSTALLED_APPS = [
    # ... Django apps ...
    'core',
    'accounts',
    'referrals',
    'masterdata',
    'profiles',
    'availability',
]
```

---

## Core Ownership Rule (LOCKED)

✅ **One Pandit → Many Availability entries**
- A Pandit can have multiple availability entries
- Each entry represents a time window

✅ **Availability belongs exclusively to Pandit**
- No user/customer references
- No booking references
- Pandit-only ownership

✅ **Availability does NOT belong to users, leads, or bookings**
- No foreign keys to users (except Pandit)
- No foreign keys to bookings
- No lead tracking fields

---

## What This Model Does NOT Contain

❌ **Booking references**
- No booking foreign keys
- No booking status fields
- Booking is separate (Module 8)

❌ **Customer/user references**
- No user foreign keys (except Pandit owner)
- No customer tracking
- No user-specific availability

❌ **Payment fields**
- No payment references
- No pricing fields
- Payment is separate

❌ **Lead / KPI counters**
- No lead tracking
- No conversion metrics
- No KPI fields

❌ **Slot locks**
- No locking mechanism
- No reservation fields
- Availability is signal, not commitment

❌ **Demand metrics**
- No demand tracking
- No popularity scores
- No analytics fields

❌ **Trust or SEO fields**
- No trust calculation fields
- No SEO fields
- Trust/SEO are separate modules

---

## Data Normalization Rules

✅ **City, Area, Pooja → referenced from Module 2**
- Uses ForeignKey to masterdata models
- No duplication of master data
- PROTECT on delete (master data protection)

✅ **No duplication of master data**
- All location/pooja data from masterdata app
- Single source of truth

✅ **No denormalized analytics**
- No cached counts
- No aggregated metrics
- Pure normalized structure

---

## Model Relationships

### Foreign Keys (Outgoing)
- `pandit` → `accounts.User` (CASCADE)
- `city` → `masterdata.City` (PROTECT)
- `area` → `masterdata.LocalArea` (PROTECT, optional)
- `pooja` → `masterdata.Pooja` (PROTECT, optional)

### Reverse Relations (Incoming)
- `User.availabilities` → Many Availability entries
- `City.availabilities` → Many Availability entries
- `LocalArea.availabilities` → Many Availability entries
- `Pooja.availabilities` → Many Availability entries

---

## Verification Results

### ✅ Scope Compliance
- **Status:** PASS
- **Models Only:** Confirmed
- **No Views:** Confirmed
- **No Serializers:** Confirmed
- **No APIs:** Confirmed
- **No Business Logic:** Confirmed (only validation)

### ✅ Model Design
- **Status:** PASS
- **Booking-Agnostic:** ✅
- **Payment-Agnostic:** ✅
- **KPI-Agnostic:** ✅
- **Search-Friendly:** ✅ (indexes added)
- **Extensible:** ✅

### ✅ Architectural Alignment
- **Status:** PASS
- **Aligned with Task 6.1 (Strategy):** ✅
- **Aligned with Module 2 (Master Data):** ✅
- **Aligned with Module 1 (User Model):** ✅
- **Ready for Task 6.3 (Input Rules):** ✅

---

## Rules Compliance

### ✅ MODELS ONLY Principle
- ✅ Django model created
- ✅ No views created
- ✅ No serializers created
- ✅ No APIs created
- ✅ No business logic (only validation)

### ✅ Clear and Unambiguous
- ✅ Model structure clearly defined
- ✅ Relationships explicitly stated
- ✅ Validation rules documented
- ✅ Ownership rules enforced

### ✅ Architectural Alignment
- ✅ Aligned with Task 6.1 strategy
- ✅ Uses Module 2 master data
- ✅ Pandit-only ownership
- ✅ Ready for future extensions

---

## Next Steps

**Task 6.2 is complete and locked.**

Ready to proceed to:
- **Module 6 → Task 6.3:** Pandit Availability Input Rules (Calendar-Based) (NO CODE)

**Important:**
- Availability model is created and ready for migration
- Model is booking-agnostic and extensible
- Foundation is stable and ready for Task 6.3

---

## Notes

- ✅ Availability model follows Task 6.1 strategy
- ✅ Model is passive and descriptive
- ✅ No booking, payment, or KPI fields
- ✅ Uses master data from Module 2
- ✅ Pandit-only ownership (enforced at service layer, not DB level)
- ✅ No audit model implemented; audit deferred to Task 6.12
- ✅ No save() override; validation enforcement deferred to service layer

---

**Status:** ✅ Task 6.2 Complete & Locked - Availability Data Model Created (FULLY COMPLIANT)  
**Module 6:** Task 6.2 COMPLETE & LOCKED  
**Type:** Models Only (Data Structure)  
**Compliance:** All 4 verification issues fixed (MODELS ONLY, role enforcement, recurrence, audit deferral)  
**Ready for:** Task 6.3 - Pandit Availability Input Rules (Calendar-Based) (NO CODE)

