# Upload Images: Sizes, Railway & GoDaddy VPS

This doc covers **recommended image sizes** for all uploads, **why images disappear on Railway** after upload, and how to fix it on **Railway** and **GoDaddy VPS**. Same codebase works for all roles and places.

---

## Why images don’t display on Railway after upload

On **Railway** (and similar PaaS), the app runs in a **container with an ephemeral filesystem**:

- Uploaded files are saved to `MEDIA_ROOT` (e.g. `media/profiles/pandit_images/photo.jpg`).
- On **redeploy** or **restart**, the container is recreated and that filesystem is **wiped**.
- The database still has the path, but the file is gone → **404** when the browser requests `/media/...`.

So the issue is **not** image size or format; it’s **storage persistence**. Fix: use **persistent storage** for media (Railway Volume or S3).

---

## Recommended image sizes (all roles and places)

Use these as guidelines. The app allows up to **25 MB per image** by default (configurable). Keeping files smaller and correctly sized improves load times and display.

| Upload type | Where | Recommended size / dimensions | Max size (default) | Format |
|-------------|--------|--------------------------------|--------------------|--------|
| **Pandit profile photo** | Pandit profile edit | 400×400 px (square), 500 KB–1 MB | 25 MB | JPG, PNG, WEBP |
| **Pandit cover photo** | Pandit profile edit | 1920×600 px, 1–2 MB | 25 MB | JPG, PNG, WEBP |
| **User profile picture** | Account → Profile settings | 400×400 px (square), &lt; 500 KB | 25 MB | JPG, PNG, WEBP |
| **Page cover image** | Temple/Page edit | 1920×600 px or 16:9 | 25 MB | JPG, PNG, WEBP |
| **Page profile image** | Temple/Page edit | 400×400 px (square) | 25 MB | JPG, PNG, WEBP |
| **Navbar / footer / email logo** | Branding → Manage logos | 200×200 px or 100–800 px width, &lt; 500 KB | 25 MB | PNG, WEBP, SVG* |
| **Favicon** | Branding / CMS | 16×16 or 32×32 px | 25 MB | ICO, PNG |
| **CMS OG image** | Content Management (SEO) | 1200×630 px | 25 MB | JPG, PNG, WEBP |
| **Page gallery** | Page gallery upload | 1200×800 px or similar | 25 MB | JPG, PNG, WEBP |
| **Ad banners (desktop)** | Super Admin → Advertisements | Top 970×90, Sidebar 300×250, Footer 728×90, In Content 336×280, Dashboard Top 728×90, Dashboard Sidebar 250×250 | 1 MB | JPG, PNG, WEBP |
| **Ad banners (mobile)** | Same form, “Mobile image” field | 320×50 (leaderboard) or 320×100; shown on screens ≤768px when set | 1 MB | JPG, PNG, WEBP |

\* SVG may be restricted by your file-upload security allowlist; PNG/WEBP are always safe.

**Full ad sizes and placements:** see **ADS_BANNER_SIZES.md**.

These apply for **all roles** (Pandit, User, Admin Pandit, Super Admin) and **all places** (profile edit, page edit, branding, CMS, gallery, ads). Validation is centralized in `core.file_upload_security`.

---

## Fix: Railway – persistent media (so images display after redeploy)

You must store uploads on **persistent storage**. Two options.

### Option A: Railway Volume (recommended if you stay on Railway)

1. In Railway → your **web service** → **Settings** (or **Variables**).
2. Add a **Volume**:
   - **“Add Volume”** or **“Volumes”**.
   - Mount path: e.g. **`/data`** (Railway will create it inside the container).
3. Set an environment variable so the app uses this path for media:
   - Variable: **`MEDIA_ROOT`**
   - Value: **`/data/media`**
   (or use **`RAILWAY_VOLUME_MOUNT_PATH`** if you use the convention below.)
4. Redeploy. The app will write uploads to `/data/media`, which is on the volume and **persists** across deploys. Images will keep displaying.

The project’s **prod** settings support overriding `MEDIA_ROOT` via the **`MEDIA_ROOT`** (or **`RAILWAY_VOLUME_MOUNT_PATH`**) environment variable so the app uses the volume path automatically.

### Option B: External storage (e.g. AWS S3, Cloudinary)

- Configure Django to use **S3** (or similar) for `DEFAULT_FILE_STORAGE` and set the bucket/credentials in env.
- Media files are then stored in the cloud and served from there; no dependency on the container filesystem. Works on Railway, GoDaddy VPS, and anywhere.

---

## GoDaddy VPS (and any server with a persistent disk)

On a **VPS** (GoDaddy or other), the server disk is **persistent**:

- Set **`MEDIA_ROOT`** to a path on that disk (e.g. `/var/www/nityadharma/media` or `BASE_DIR / 'media'` if the app directory is on the same disk).
- Ensure the app (or nginx) serves **`/media/`** from that directory (the project already serves it when `SERVE_MEDIA_IN_PROD` is True).
- No Volume or S3 required for basic persistence. Same upload code and image sizes apply for all roles and places.

---

## Checklist (all roles / places)

- **Pandit:** Profile image, cover image (profile edit).
- **User:** Profile picture (account profile settings).
- **Pages (Temple/Brand/Trust/Social):** Cover image, profile image, gallery images (page edit / gallery upload).
- **Super Admin:** Branding logos (navbar, footer, email, favicon), CMS OG images, **ad banners (desktop + optional mobile image)**. Ad images use the same `MEDIA_ROOT`; on Railway use a Volume so ads persist (see above).
- **CMS:** OG image, organization logo (Content Management).

Use the **recommended sizes** above for best display and performance. After fixing **persistent storage on Railway** (Volume or S3), uploads will display correctly on Railway and on GoDaddy VPS with the same codebase.
