# Page Management UI Contract

## 📋 Overview

This document defines the **UI contract** for page management features. It specifies what UI elements should appear, what actions are allowed per role, and what should NEVER appear in the UI.

**Purpose:** Prevent future UI mistakes and ensure consistent role-based access control.

---

## 🔐 Role Definitions

### Admin Pandit
- **Role:** `role='admin'` AND `is_superuser=False`
- **Can Create:** ONLY Temple pages
- **Can Manage:** Only pages they created
- **Cannot:** Make pages invisible, create other page types

### Super Admin
- **Role:** `is_superuser=True`
- **Can Create:** ALL page types (Temple, Brand, Trust, Social Service)
- **Can Manage:** ALL pages (regardless of creator)
- **Can:** Make pages invisible, manage any page

---

## 🎨 UI Elements by Role

### Admin Pandit Dashboard

#### ✅ SHOW These Buttons/Actions:
- **Create Temple Page** button (only Temple, no other types)
- **Edit Page** button (only for pages they created)
- **Deactivate Page** button (only for pages they created)
- **Activate Page** button (only for pages they created)
- **View Page** link (for all their pages)

#### ❌ NEVER Show:
- Create Brand/Trust/Social Service page buttons
- Make Page Invisible button
- Delete Page button (hard delete forbidden)
- Edit buttons for pages created by others
- Deactivate/Activate buttons for pages created by others

#### 📊 Dashboard Data Display:
- Total pages created (by this Admin Pandit)
- Active pages count
- Deactivated pages count
- Referral links count (if available)
- Last created page preview

---

### Super Admin Dashboard

#### ✅ SHOW These Buttons/Actions:
- **Create Page** button (with dropdown: Temple, Brand, Trust, Social Service)
- **Edit Page** button (for any page)
- **Deactivate Page** button (for any page)
- **Activate Page** button (for any page)
- **Make Page Invisible** button (for any page)
- **View Page** link (for all pages)

#### ❌ NEVER Show:
- Delete Page button (hard delete forbidden)
- Any role-based restrictions on page management

#### 📊 Dashboard Data Display:
- Total pages (system-wide)
- Pages by type (Temple, Brand, Trust, Social Service)
- Pages by status (Active, Deactivated, Invisible)
- Deactivated pages count
- Invisible pages count

---

## 📄 Page Status Visual Indicators

### ACTIVE Status
- **Visual:** Normal display, no banner
- **Access:** Visible to all users
- **Actions Available:**
  - Admin Pandit: Edit, Deactivate (if owner)
  - Super Admin: Edit, Deactivate, Make Invisible

### DEACTIVATED Status
- **Visual:** Page visible with banner: **"This page is deactivated"**
- **Access:** Visible to all users (with status banner)
- **Actions Available:**
  - Admin Pandit: Edit, Activate (if owner)
  - Super Admin: Edit, Activate, Make Invisible

### INVISIBLE Status
- **Visual:** Page visible with banner: **"This page is invisible"** (if accessible)
- **Access:**
  - **Super Admin:** Always visible (with banner)
  - **Admin Pandit:** Visible only if they created it (with banner)
  - **Others:** Not accessible (404-like response)
- **Actions Available:**
  - Super Admin: Edit, Activate, Make Visible
  - Admin Pandit: Edit, Activate (if owner, but cannot make invisible)

---

## 🚫 What NEVER Appears in UI

### Hard Delete
- ❌ **NO Delete Page button anywhere**
- ❌ **NO Delete confirmation dialogs**
- ❌ **NO Permanent deletion options**
- **Reason:** Pages are NEVER hard-deleted. Use status changes (Deactivate/Invisible) for soft deletion.

### Unauthorized Actions
- ❌ **NO Create buttons for page types user cannot create**
  - Admin Pandit should NOT see "Create Brand Page" button
- ❌ **NO Edit/Manage buttons for pages user cannot modify**
  - Admin Pandit should NOT see edit buttons for pages created by others
- ❌ **NO Make Invisible button for Admin Pandit**
  - Only Super Admin can make pages invisible

### Status Confusion
- ❌ **NO "Delete" terminology**
  - Use "Deactivate" or "Make Invisible" instead
- ❌ **NO Permanent removal language**
  - All actions are reversible via status changes

---

## 🔄 Action Flow Examples

### Admin Pandit Creating a Temple Page
1. User clicks "Create Temple Page" button
2. Form shows: Title, Slug, Description
3. On submit: `create_page(user, 'TEMPLE', payload)`
4. Success: Page created, redirect to page list
5. Error: Show validation/permission error

### Admin Pandit Deactivating Their Page
1. User clicks "Deactivate" on their page
2. Confirmation: "Are you sure you want to deactivate this page?"
3. On confirm: `deactivate_page(user, page_public_id)`
4. Success: Page status → DEACTIVATED, show banner
5. Error: Show permission error if not owner

### Super Admin Making Page Invisible
1. User clicks "Make Invisible" on any page
2. Confirmation: "This page will be hidden from listings but accessible via direct URL"
3. On confirm: `make_page_invisible(user, page_public_id)`
4. Success: Page status → INVISIBLE, hidden from listings
5. Error: Should not occur (Super Admin has permission)

---

## 📍 Page Access Rules

### Public Page View (via URL)
- **ACTIVE:** Visible to all, no banner
- **DEACTIVATED:** Visible to all, show banner "This page is deactivated"
- **INVISIBLE:**
  - Super Admin: Visible with banner "This page is invisible"
  - Admin Pandit (creator): Visible with banner "This page is invisible"
  - Others: 404 Not Found

### Page Listing (Dashboard)
- **Admin Pandit:** Shows only their pages (ACTIVE + DEACTIVATED, excludes INVISIBLE)
- **Super Admin:** Shows all pages (all statuses)

---

## 🎯 Button Visibility Matrix

| Action | Admin Pandit (Own Page) | Admin Pandit (Other's Page) | Super Admin |
|--------|------------------------|----------------------------|-------------|
| Create Temple Page | ✅ | ✅ | ✅ |
| Create Brand/Trust/Social Service | ❌ | ❌ | ✅ |
| Edit Page | ✅ | ❌ | ✅ |
| Deactivate Page | ✅ | ❌ | ✅ |
| Activate Page | ✅ | ❌ | ✅ |
| Make Invisible | ❌ | ❌ | ✅ |
| Delete Page | ❌ | ❌ | ❌ |

---

## 📝 Form Fields

### Create Page Form
- **Title** (required, max 200 chars)
- **Slug** (optional, auto-generated from title if not provided)
- **Description** (optional, text area)
- **Page Type** (dropdown, filtered by role):
  - Admin Pandit: Only "Temple"
  - Super Admin: "Temple", "Brand", "Trust", "Social Service"

### Edit Page Form
- Same fields as Create
- Cannot change `page_type` after creation
- Cannot change `created_by` (immutable)

---

## 🔍 Search & Filtering

### Admin Pandit Dashboard
- Filter by: Status (Active, Deactivated)
- Search by: Title, Description
- **Excludes:** INVISIBLE pages (not shown in list)

### Super Admin Dashboard
- Filter by: Page Type, Status (All statuses)
- Search by: Title, Description, Creator
- **Includes:** All pages (all statuses)

---

## ⚠️ Error Messages

### Permission Denied
- **Message:** "You do not have permission to perform this action."
- **When:** User tries to perform action they're not allowed to do

### Page Not Found
- **Message:** "Page not found or you do not have access to view this page."
- **When:** User tries to access INVISIBLE page they cannot view

### Validation Error
- **Message:** Show specific validation error (e.g., "Slug already exists for this page type")
- **When:** Form validation fails

---

## 🔐 Security Reminders

1. **Always validate permissions server-side**
   - UI can hide buttons, but backend must enforce permissions
   - Use `pages/services.py` functions which enforce permissions

2. **Use public_id in URLs**
   - Never expose internal BIGINT IDs
   - All page URLs use `public_id` (UUIDv7)

3. **Audit all actions**
   - All page actions are logged in `PageAuditLog`
   - UI should not bypass audit logging

4. **No hard deletes**
   - UI should never provide delete functionality
   - Use status changes (Deactivate/Invisible) instead

---

## 📚 Backend Functions Reference

### Page Creation
```python
from pages.services import create_page

# Admin Pandit: Only TEMPLE
page = create_page(user, 'TEMPLE', {
    'title': 'My Temple',
    'slug': 'my-temple',
    'description': 'Description here'
})

# Super Admin: Any type
page = create_page(user, 'BRAND', {...})
```

### Page Status Management
```python
from pages.services import deactivate_page, activate_page, make_page_invisible

# Deactivate (Admin Pandit: own pages only, Super Admin: any)
deactivate_page(user, page_public_id)

# Activate (Admin Pandit: own pages only, Super Admin: any)
activate_page(user, page_public_id)

# Make Invisible (Super Admin only)
make_page_invisible(user, page_public_id)
```

### Page Access
```python
from pages.selectors import get_page_by_public_id

# Returns dict with page + visibility metadata
result = get_page_by_public_id(user, page_public_id)
if result and result['is_visible']:
    page = result['page']
    show_banner = result['show_banner']
    banner_message = result['banner_message']
```

### Dashboard Data
```python
from pages.dashboard_data import get_admin_pandit_page_dashboard, get_super_admin_page_overview

# Admin Pandit dashboard
data = get_admin_pandit_page_dashboard(user)

# Super Admin dashboard
overview = get_super_admin_page_overview()
```

---

## ✅ Checklist for UI Implementation

Before implementing UI, verify:

- [ ] Buttons shown match role permissions
- [ ] No delete buttons anywhere
- [ ] Status banners displayed correctly
- [ ] INVISIBLE pages handled correctly (404 for unauthorized)
- [ ] All actions use `public_id` in URLs
- [ ] Form validations match backend rules
- [ ] Error messages are user-friendly
- [ ] Audit logs are created for all actions
- [ ] No hard delete functionality
- [ ] Page type dropdown filtered by role

---

## 📞 Questions?

If unsure about UI behavior:
1. Check this document first
2. Review `pages/services.py` for permission rules
3. Review `pages/selectors.py` for access control
4. Never assume - always validate with backend functions

---

**Last Updated:** 2026-01-12  
**Version:** 1.0  
**Status:** Active






















