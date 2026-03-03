# Deploy Nitya Dharma to Vercel (for testing)

Vercel runs Django as a **serverless function**. Good for quick testing; for long-term production, Render is better (no 10s timeout, persistent processes).

---

## Before you start

1. Code is on GitHub: **Nitya-Dharma/Nitya_Dharma_project**
2. You have a **Vercel account** (sign up at [vercel.com](https://vercel.com) with GitHub).
3. For a **database**: use the same **Render PostgreSQL** `DATABASE_URL` (or any Postgres URL). Vercel does not provide a database.

---

## Step 1: Push latest code

Make sure these are committed and pushed to GitHub:

- `vercel.json`
- `nityadharma/wsgi.py` (with `app = application`)
- `nityadharma/settings/base.py` (WSGI_APPLICATION = `nityadharma.wsgi.app`)
- `nityadharma/settings/prod.py` (includes `.vercel.app` in ALLOWED_HOSTS when VERCEL=1)

```bash
git add .
git commit -m "Add Vercel deployment config"
git push origin main
```

---

## Step 2: Import project in Vercel

1. Go to **[vercel.com](https://vercel.com)** and log in (use **Continue with GitHub**).
2. Click **Add New…** → **Project**.
3. Under **Import Git Repository**, find **Nitya-Dharma/Nitya_Dharma_project** (or paste the repo URL).
4. Click **Import**.

---

## Step 3: Configure project (before first deploy)

On the **Configure Project** page:

### 3.1 Project name (optional)

- **Project Name**: e.g. `nityadharma` (your app will be at `nityadharma.vercel.app`).

### 3.2 Framework Preset

- Set to **Other** or **Django** if shown. Do **not** use Next.js.

### 3.3 Build and output

- **Build Command**:  
  `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Output Directory**: leave **empty** (we use serverless, not static export).
- **Install Command**: leave empty (we install in the build command).

### 3.4 Root directory

- **Root Directory**: leave **empty** (repo root is the project root).

### 3.5 Environment variables

Click **Environment Variables** and add (for **Production**, and optionally **Preview**):

| Name | Value |
|------|--------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` |
| `SECRET_KEY` | Your secret key (same as Render or a new one) |
| `DEBUG` | `False` |
| `DATABASE_URL` | Your full PostgreSQL URL (e.g. from Render: `postgresql://user:pass@host/dbname`) |
| `ALLOWED_HOSTS` | Leave empty (`.vercel.app` is added automatically when `VERCEL=1`). |

Vercel sets `VERCEL=1` automatically; the app will add `.vercel.app` to `ALLOWED_HOSTS` in prod settings.

---

## Step 4: Deploy

1. Click **Deploy**.
2. Wait for the build to finish (first time can take a few minutes).
3. When it’s done, open the **Visit** link (e.g. `https://nityadharma-xxx.vercel.app`).

---

## Step 5: Run migrations (first time only)

Vercel does **not** give you a Shell. So you have two options:

### Option A – Migrate from your PC (easiest for testing)

From your **local** project folder, point Django at the **same** Postgres DB and run migrations once:

```bash
# Use the same DATABASE_URL as in Vercel (e.g. from Render PostgreSQL)
set DATABASE_URL=postgresql://user:pass@host/dbname
set DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
python manage.py migrate
```

(On Mac/Linux use `export` instead of `set`.)

After that, the Vercel app will use the same DB and tables.

### Option B – Migrate on Render (if DB is on Render)

If your Postgres is the one you use on Render:

1. Open your **Render** Web Service → **Shell**.
2. Run:  
   `python manage.py migrate`  
   (and `createsuperuser` if you want).

The Vercel app uses the same `DATABASE_URL`, so it will see the same database and tables.

---

## Step 6: Check the app

- Open the Vercel URL (e.g. `https://your-project.vercel.app`).
- You should see your Django app (login, home, etc.).
- If you see 500 or “DisallowedHost”, check **Vercel → Project → Settings → Environment Variables** and logs under **Deployments → [latest] → Functions / Runtime Logs**.

---

## Limits (testing only)

- **Execution timeout**: ~10 seconds per request (Hobby). Long requests can fail.
- **Cold starts**: First request after idle can be slow.
- **No persistent disk**: File uploads (e.g. to `media/`) are not stored between requests unless you use external storage (e.g. S3).

For real production and full features, keep using **Render** (or another always-on host).

---

## Summary checklist

- [ ] Pushed `vercel.json` and wsgi/settings changes to GitHub  
- [ ] Created Vercel project and imported repo  
- [ ] Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`  
- [ ] Set env: `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `DEBUG`, `DATABASE_URL`  
- [ ] Deployed and opened the Vercel URL  
- [ ] Ran `migrate` (locally or on Render) so the DB has tables  
