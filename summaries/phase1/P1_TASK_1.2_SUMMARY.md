# Task 1.2 - Create Custom User Model Summary

## Overview
Successfully created a custom User model for the Nitya Dharma platform. This is the foundation for all user-related functionality including authentication, roles, and status management.

## Changes Made

### 1. Created Accounts App
- **Command:** `python manage.py startapp accounts`
- **Location:** `accounts/` directory at project root
- **Status:** App created with default Django structure

### 2. Created Custom User Model
**File:** `accounts/models.py`

**Model Details:**
- **Base Class:** `AbstractUser` (extends Django's AbstractUser)
- **Primary Identifier:** `email` (unique, used for login)
- **Display Name:** `username` (optional, for display only)
- **Role Field:** Choices: `user`, `pandit`, `admin` (default: `user`)
- **Status Field:** Choices: `pending`, `active`, `rejected` (default: `pending`)
- **Timestamps:** `created_at`, `updated_at`

**Key Features:**
```python
USERNAME_FIELD = 'email'  # Email is used for authentication
REQUIRED_FIELDS = []      # Only email and password required
```

### 3. Updated Settings
**File:** `nityadharma/settings/base.py`

**Changes:**
- Added `'accounts'` to `INSTALLED_APPS`
- Set `AUTH_USER_MODEL = 'accounts.User'`

**Before:**
```python
INSTALLED_APPS = [
    # ... Django apps ...
    'core',
]
```

**After:**
```python
INSTALLED_APPS = [
    # ... Django apps ...
    'core',
    'accounts',
]

# Custom User Model
# Must be set before first migration
AUTH_USER_MODEL = 'accounts.User'
```

### 4. Created and Applied Migrations
- **Migration Created:** `accounts/migrations/0001_initial.py`
- **Migration Applied:** Successfully
- **Database Table:** `accounts_user` created

## User Model Structure

### Fields

#### Authentication Fields
- **`email`** (EmailField, unique=True)
  - Primary identifier for login
  - Required field
  - Unique constraint

- **`username`** (CharField, optional)
  - Display name only
  - Not used for authentication
  - Can be null/blank

- **`password`** (CharField)
  - Hashed password (handled by Django)
  - Inherited from AbstractUser

#### Role & Status Fields
- **`role`** (CharField with choices)
  - Choices: `user`, `pandit`, `admin`
  - Default: `user`
  - Determines user permissions and access

- **`status`** (CharField with choices)
  - Choices: `pending`, `active`, `rejected`
  - Default: `pending`
  - Controls account activation state

#### Inherited Fields (from AbstractUser)
- `first_name` (CharField, optional)
- `last_name` (CharField, optional)
- `is_staff` (BooleanField) - Admin access
- `is_active` (BooleanField) - Account active status
- `is_superuser` (BooleanField) - Superuser status
- `date_joined` (DateTimeField) - Registration date
- `last_login` (DateTimeField) - Last login timestamp
- `groups` (ManyToManyField) - Permission groups
- `user_permissions` (ManyToManyField) - User permissions

#### Custom Timestamps
- **`created_at`** (DateTimeField, auto_now_add)
  - When user account was created

- **`updated_at`** (DateTimeField, auto_now)
  - Last profile update timestamp

### Model Configuration

```python
USERNAME_FIELD = 'email'      # Email is used for login
REQUIRED_FIELDS = []          # Only email and password required
```

### Meta Options
- **Verbose Name:** "User"
- **Verbose Name Plural:** "Users"
- **Database Table:** `accounts_user`

## Why AbstractUser?

### Benefits
1. **Pre-built Functionality**
   - Password hashing
   - Permission system
   - Group management
   - Authentication methods

2. **Django Integration**
   - Works with Django admin
   - Compatible with auth views
   - Supports Django permissions

3. **Extensibility**
   - Easy to add custom fields
   - Can override methods
   - Maintains Django standards

### Why Not AbstractBaseUser?
- AbstractBaseUser requires implementing everything from scratch
- More complex and error-prone
- AbstractUser provides the right balance of customization and convenience

## Why AUTH_USER_MODEL Must Be Set Early

### Critical Timing
- **Must be set BEFORE first migration**
- **Cannot be changed after migrations**
- **All foreign keys reference this model**

### Impact
- If changed later, all foreign keys break
- Requires complex data migration
- High risk of data loss
- This is why we set it NOW, before any other models exist

## Migration Details

### Migration File
**Location:** `accounts/migrations/0001_initial.py`

**Operations:**
- Creates `accounts_user` table
- Includes all fields from AbstractUser
- Adds custom fields: `email`, `username`, `role`, `status`, `created_at`, `updated_at`
- Sets up relationships: `groups`, `user_permissions`

### Applied Migrations
```
✅ contenttypes.0001_initial
✅ contenttypes.0002_remove_content_type_name
✅ auth.0001_initial
✅ auth.0002_alter_permission_name_max_length
✅ auth.0003_alter_user_email_max_length
✅ auth.0004_alter_user_username_opts
✅ auth.0005_alter_user_last_login_null
✅ auth.0006_require_contenttypes_0002
✅ auth.0007_alter_validators_add_error_messages
✅ auth.0008_alter_user_username_max_length
✅ auth.0009_alter_user_last_name_max_length
✅ auth.0010_alter_group_name_max_length
✅ auth.0011_update_proxy_permissions
✅ auth.0012_alter_user_first_name_max_length
✅ accounts.0001_initial  ← Our custom User model
✅ admin.0001_initial
✅ admin.0002_logentry_remove_auto_add
✅ admin.0003_logentry_add_action_flag_choices
✅ sessions.0001_initial
```

## Verification Results

### ✅ Django System Check
- **Status:** PASS
- **Result:** No issues detected
- **Command:** `python manage.py check`

### ✅ Model Import
- **Status:** PASS
- **Result:** User model imports successfully
- **AUTH_USER_MODEL:** `accounts.User`

### ✅ Settings Configuration
- **Status:** PASS
- **AUTH_USER_MODEL:** Set to `accounts.User`
- **INSTALLED_APPS:** `accounts` app registered

### ✅ Migration Status
- **Status:** PASS
- **Migration Created:** `0001_initial.py`
- **Migration Applied:** Successfully
- **Database Table:** `accounts_user` created

### ✅ Database Verification
- **Status:** PASS
- **Tables Created:** User table exists
- **No Errors:** Database structure correct

## What Was NOT Done (As Required)

✅ **No Authentication Views** - No login, register, or logout views
✅ **No Templates** - No authentication templates created
✅ **No Admin Customization** - Default admin only (Task 1.3)
✅ **No Profile Models** - No additional profile models
✅ **No Referral Logic** - No referral fields or relationships
✅ **No Permissions Logic** - No custom permissions defined
✅ **No URL Routes** - No authentication URLs

## Project Structure After Task 1.2

```
Nitya Dharma/
├── accounts/                    # ← NEW: Accounts app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py               # ← NEW: Custom User model
│   ├── tests.py
│   ├── views.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py     # ← NEW: User model migration
├── core/
├── nityadharma/
│   ├── settings/
│   │   ├── base.py             # ← Updated: AUTH_USER_MODEL set
│   │   ├── dev.py
│   │   └── prod.py
│   └── ...
└── ...
```

## Database Schema

### accounts_user Table

**Columns:**
- `id` (BigAutoField, Primary Key)
- `password` (CharField)
- `last_login` (DateTimeField, nullable)
- `is_superuser` (BooleanField)
- `first_name` (CharField, nullable)
- `last_name` (CharField, nullable)
- `is_staff` (BooleanField)
- `is_active` (BooleanField)
- `date_joined` (DateTimeField)
- `email` (EmailField, unique) ← Custom field
- `username` (CharField, nullable, unique) ← Custom field
- `role` (CharField, choices) ← Custom field
- `status` (CharField, choices) ← Custom field
- `created_at` (DateTimeField) ← Custom field
- `updated_at` (DateTimeField) ← Custom field

**Relationships:**
- Many-to-Many: `groups` (auth.Group)
- Many-to-Many: `user_permissions` (auth.Permission)

## Next Steps

Task 1.2 is complete. Ready to proceed to:
- **Task 1.3:** Configure Django Admin for Custom User (minimal)

## Notes

- Custom User model is now the foundation for all user-related functionality
- Email-based authentication is configured
- Role and status fields are ready for use
- Database table is created and ready
- No authentication views or templates yet (will be added in later tasks)
- Admin customization will be done in Task 1.3

---

**Status:** ✅ Task 1.2 Complete - Custom User Model Created
**Database:** ✅ Migrations Applied
**Ready for:** Task 1.3 - Admin Configuration












