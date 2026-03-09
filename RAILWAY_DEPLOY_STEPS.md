# Deploy Nitya Dharma to Railway – Step-by-Step (Testing)

You can use **PostgreSQL** (default) or **MySQL** on Railway. Your `prod.py` supports both.

- **PostgreSQL:** Railway adds `DATABASE_URL` automatically (Steps 4–5 below).
- **MySQL:** Add a MySQL service and use `MYSQL_URL` (see **[Using MySQL instead of PostgreSQL](#using-mysql-instead-of-postgresql)** at the end.

---

## Step 1: Push your code to GitHub

1. Open terminal in project folder:
   ```bash
   cd "c:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"
   ```
2. Commit and push (if not already done):
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```
3. Confirm the repo **Nitya-Dharma/Nitya_Dharma_project** is up to date on GitHub.

---

## Step 2: Sign up / log in to Railway

1. Go to **https://railway.app**
2. Click **“Login”** or **“Start a New Project”**
3. Choose **“Login with GitHub”** and authorize Railway to access your GitHub account
4. Complete sign-up if first time

---

## Step 3: Create a new project from GitHub

1. On the Railway dashboard, click **“New Project”**
2. Select **“Deploy from GitHub repo”**
3. If asked, connect your GitHub account and allow access to **Nitya-Dharma**
4. Choose the repo: **Nitya-Dharma/Nitya_Dharma_project**
5. Click **“Deploy now”** (Railway will create a service and try to build; we will add a database and env vars next)

---

## Step 4: Add a PostgreSQL database

1. In your project, click **“+ New”** (or **“Add service”**)
2. Select **“Database”** → **“PostgreSQL”**
3. Wait until the Postgres service is **Running**
4. Click the **Postgres** service → **“Variables”** or **“Connect”** tab  
   - Railway automatically creates a variable **`DATABASE_URL`** for this database
5. We will attach this to the web app in the next step (usually via “Reference” or “Add to project”)

---

## Step 5: Attach DATABASE_URL to the web service

1. Click your **web service** (the one from GitHub, not Postgres)
2. Go to **“Variables”** (or **“Settings”** → **Variables**)
3. Click **“+ New Variable”** or **“Add variable”**
4. If Railway shows **“Add a reference”** or **“Variable reference”**:
   - Choose the **Postgres** service
   - Select **`DATABASE_URL`** and add it to the web service  
   So the web app gets `DATABASE_URL` from the Postgres service.
5. If there is no “reference” option, go to the **Postgres** service → **Variables** tab, copy the value of **`DATABASE_URL`**, then in the **web service** → **Variables**, add:
   - **Name:** `DATABASE_URL`
   - **Value:** (paste the copied URL)

---

## Step 6: Set required environment variables (web service)

1. Stay in the **web service** → **Variables**
2. Add these variables one by one (click **“+ New Variable”** or **“Raw Editor”**):

| Variable | Value | Notes |
|----------|--------|--------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` | **Required** – use prod settings |
| `SECRET_KEY` | (a long random string) | **Required** – e.g. generate with Python: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | Recommended for testing; use `True` only if you need debug page |
| `ALLOWED_HOSTS` | `*` | For testing only; or leave default in prod.py |

3. **Optional (Railway often sets these):**
   - `PORT` – Railway sets this automatically; your `gunicorn.conf.py` uses it.
   - `RAILWAY_PUBLIC_DOMAIN` – Railway sets this when you generate a domain; your `prod.py` already adds `.railway.app` to `ALLOWED_HOSTS` when this is set.

4. Save / Apply the variables. Railway will usually redeploy when variables change.

---

## Step 6b (optional): Python version

- The project includes a **`runtime.txt`** with `python-3.11.9` so Railway uses a consistent Python version. If Railway ignores it, you can set **NIXPACKS_PYTHON_VERSION** (or the equivalent in Settings) to `3.11`.

---

## Step 7: Set build and start commands (if needed)

1. Click the **web service** → **“Settings”** (or **“Configure”**)
2. **Build Command** (optional but recommended so static files are collected):
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
   If Railway already runs `pip install -r requirements.txt` by default, you can use only:
   ```bash
   python manage.py collectstatic --noinput
   ```
3. **Start Command** (optional – Railway should detect **Procfile**):
   - If it uses the Procfile, you should see: `web: gunicorn nityadharma.wsgi:application --config gunicorn.conf.py`
   - If you must set it manually:  
     **Start Command:** `gunicorn nityadharma.wsgi:application --config gunicorn.conf.py`
4. **Root Directory** (optional): leave blank unless your app is in a subfolder (yours is at repo root).
5. Save.

---

## Step 8: Run migrations (first deploy)

After the first successful build and deploy:

**Option A – Railway CLI (recommended)**

1. Install Railway CLI: https://docs.railway.app/develop/cli  
   (e.g. Windows: `winget install Railway.CLI` or use npm: `npm i -g @railway/cli`)
2. In your project folder:
   ```bash
   railway login
   railway link
   ```
   Choose the project and the **web** service when asked.
3. Run migrations:
   ```bash
   railway run python manage.py migrate
   ```
4. (Optional) Create a superuser:
   ```bash
   railway run python manage.py createsuperuser
   ```

**Option B – Deploy hook / one-off command (if your plan supports it)**

- In Railway dashboard, open your **web service** → **“Settings”** or **“Deploy”**
- If there is a **“One-off command”** or **“Run command”**, run:
  ```bash
  python manage.py migrate
  ```

**Option C – Build command (run every deploy)**

- You can add to **Build Command**:
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
  ```
  Then migrations run on every build (fine for testing; for production you may prefer running them once or via release phase).

---

## Step 9: Generate a public URL

1. Click the **web service**
2. Open **“Settings”** → **“Networking”** or **“Public Networking”**
3. Click **“Generate Domain”** (or **“Add domain”**)
4. Railway will assign a URL like: `your-app-name.up.railway.app`
5. Note this URL; your app will be available at `https://<this-domain>` (Railway uses HTTPS by default)

---

## Step 10: Verify deployment

1. Open the generated URL in the browser (e.g. `https://nityadharma-project.up.railway.app`)
2. You should see your app (home or login).
3. If you see **500** or **DisallowedHost**:
   - Check **Variables** for `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, and `DATABASE_URL`
   - Ensure `ALLOWED_HOSTS` is `*` or includes your Railway domain (e.g. `.railway.app`)
4. Check **Deployments** and **Logs** in the Railway dashboard for build/runtime errors.

---

## Quick reference – required env vars (web service)

| Variable | Example / value |
|----------|------------------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` |
| `SECRET_KEY` | (50+ char random string) |
| `DATABASE_URL` | (from Postgres service – reference or copy) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` (testing only) |

---

## Optional: Redis (skip for basic testing)

- Your app runs without Redis; cache uses in-memory if `REDIS_URL` is not set.
- To add Redis later: add a **Redis** service in Railway and add **`REDIS_URL`** to the web service variables.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Build fails | **Logs** tab: missing dependency in `requirements.txt`, wrong Python version. Railway usually uses a recent Python 3. |
| 500 on open | **Logs** for Python traceback; **Variables** for `SECRET_KEY`, `DATABASE_URL`, `DJANGO_SETTINGS_MODULE`. |
| DisallowedHost | Set `ALLOWED_HOSTS=*` or add your Railway domain; ensure `RAILWAY_PUBLIC_DOMAIN` is set if your prod.py uses it. |
| Static files missing | Build command includes: `python manage.py collectstatic --noinput`. |
| DB errors | `DATABASE_URL` is from the Postgres service; migrations were run (`railway run python manage.py migrate`). |

---

## Summary checklist

- [ ] Code pushed to GitHub
- [ ] Railway project created from GitHub repo
- [ ] PostgreSQL service added and running
- [ ] `DATABASE_URL` available to web service (reference or copy)
- [ ] `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`
- [ ] `SECRET_KEY` set (long random string)
- [ ] `DEBUG=False`, `ALLOWED_HOSTS=*` (for testing)
- [ ] Build command includes `collectstatic --noinput` (and optionally `migrate`)
- [ ] Domain generated for web service
- [ ] Migrations run once (`railway run python manage.py migrate`)
- [ ] App opens in browser at the Railway URL

After this, every **git push to main** can trigger an automatic redeploy on Railway if you enabled “Deploy on push” for the service.

---

## Using MySQL instead of PostgreSQL

Yes, you can use **MySQL** on Railway for testing. The app's prod settings support it.

### 1. Add MySQL (instead of Postgres)

1. In your Railway project, click **"+ New"** (or **Ctrl/Cmd + K**).
2. Choose **"Database"** → **"MySQL"** (or search for **MySQL** in templates).
3. Wait until the MySQL service is **Running**.

### 2. Give the web service the MySQL URL

Railway's MySQL service exposes **`MYSQL_URL`** (e.g. `mysql://user:password@host:port/database`).

1. Click your **web service** → **Variables**.
2. **Option A – Reference (best):** Click **"+ New Variable"** → **"Add reference"** (or similar). Select the **MySQL** service and the variable **`MYSQL_URL`**. Add it to the web service.
3. **Option B – Copy:** Open the **MySQL** service → **Variables**, copy the value of **`MYSQL_URL`**. In the **web service** → **Variables**, add:
   - **Name:** `MYSQL_URL`
   - **Value:** (paste the URL)

**Do not set `DATABASE_URL`** when using MySQL; prod settings use **`MYSQL_URL`** for MySQL.

### 3. Other variables (same as Postgres)

Set these on the **web** service as before:

| Variable | Value |
|----------|--------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` |
| `SECRET_KEY` | (long random string) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` |

### 4. Build, migrate, domain

- **Build command:** same (e.g. `pip install -r requirements.txt && python manage.py collectstatic --noinput`).
- **Migrations:** run once: `railway run python manage.py migrate` (after linking with Railway CLI).
- **Domain:** generate a domain for the web service as in Step 9.

### Quick reference – MySQL on Railway (web service)

| Variable | Source |
|----------|--------|
| `MYSQL_URL` | From MySQL service (reference or copy) |
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` |
| `SECRET_KEY` | Your secret key |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` |

Your app already has **mysqlclient** in `requirements.txt`, so no extra packages are needed for MySQL.
