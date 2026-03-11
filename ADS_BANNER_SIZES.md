# Advertisement banner image sizes

Use these sizes for **Image Banner** ads so they display correctly on desktop and mobile. Same rules apply on **Railway**, **GoDaddy VPS**, and local; ad images use `MEDIA_ROOT` (see **UPLOAD_IMAGES_RAILWAY_VPS.md** for persistence on Railway).

---

## Desktop banner (main image)

| Placement | Minimum size (W×H px) | Typical use | Max file size |
|-----------|------------------------|-------------|----------------|
| **Top Banner** | 970×90 | Leaderboard below navbar | 1 MB |
| **Sidebar** | 300×250 | Medium rectangle | 1 MB |
| **Footer** | 728×90 | Leaderboard above footer | 1 MB |
| **In Content** | 336×280 | Large rectangle in content | 1 MB |
| **Dashboard Top** | 728×90 | Leaderboard on dashboard | 1 MB |
| **Dashboard Sidebar** | 250×250 | Square in dashboard nav | 1 MB |

**Formats:** JPG, PNG, WEBP (max 1 MB per image).  
Images **smaller** than the minimum for the chosen placement are **rejected** by validation.

---

## Mobile banner (optional mobile image)

For viewports **≤768px** the app can show a separate **Mobile image** (Super Admin → Advertisements → edit ad → **Mobile image**). If set, it is used on phones/small tablets; otherwise the desktop image is shown (scaled with `max-width: 100%`).

| Placement | Recommended mobile size (W×H px) | Notes |
|-----------|-----------------------------------|--------|
| **Top** | 320×50 | Mobile leaderboard |
| **Sidebar** | 300×250 or 320×50 | Same as desktop or 320×50 |
| **Footer** | 320×50 | Mobile leaderboard |
| **In Content** | 320×50 | Mobile leaderboard |
| **Dashboard Top** | 320×50 | Mobile leaderboard |
| **Dashboard Sidebar** | 250×250 | Same as desktop |

**Formats:** JPG, PNG, WEBP, max 1 MB.

---

## Where ads appear (all places)

- **Base layout:** Top (below navbar), Sidebar (above main content), Footer (above footer).
- **Dashboard (all roles):** Dashboard Top (above content), Dashboard Sidebar (in left nav).
- **In content:** When a slot includes “In Content” and the template includes the ad unit.

All image ads use the **responsive ad unit** (`partials/ad_unit.html`): desktop image, optional mobile image via `<picture>` and `max-width: 768px`, and `img-fluid` / `max-width: 100%` so they scale on mobile when no mobile image is set.

---

## Ads on the server (Railway / GoDaddy VPS)

- **Storage:** Ad images are stored under **`MEDIA_ROOT`** (e.g. `media/ads/banners/`, `media/ads/mobile/`). They are **not** in static files.
- **Railway:** Use a **Volume** and set **`MEDIA_ROOT`** (or **`RAILWAY_VOLUME_MOUNT_PATH`**) as in **UPLOAD_IMAGES_RAILWAY_VPS.md** so uploads (including ads) persist across deploys.
- **GoDaddy VPS:** Same code; `MEDIA_ROOT` on disk is persistent, so ad images work as long as media is served (e.g. `SERVE_MEDIA_IN_PROD = True` or nginx serving `/media/`).

---

## Quick reference

| Type | Size | When |
|------|------|------|
| Desktop banner | See table above by placement | Always (required for image ads). |
| Mobile image | 320×50 or 320×100 recommended | Optional; used on screens ≤768px when set. |
