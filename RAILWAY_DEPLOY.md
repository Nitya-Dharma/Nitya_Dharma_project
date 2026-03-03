# Deploy Nitya Dharma to Railway – Step by Step

Railway runs your Django app as a service and can provide PostgreSQL. Your project already has **Procfile**, **gunicorn**, **whitenoise**, and **DATABASE_URL** support.

---

## Before you start

1. Code is on GitHub: **Nitya-Dharma/Nitya_Dharma_project**
2. You have a **Railway** account (sign up at [railway.app](https://railway.app) with GitHub).

---

## Step 1: Push latest code (including Railway hostname support)

Make sure `nityadharma/settings/prod.py` includes `.railway.app` in ALLOWED_HOSTS when `RAILWAY_PUBLIC_DOMAIN` is set (already done if you have the latest code). Then:

```bash
git add .
git commit -m "Add Railway deployment support"
git push origin main
```

---

## Step 2: Sign in to Railway

1. Go to **[railway.app](https://railway.app)**.
2. Click **Login** and sign in with **GitHub**.
3. Authorize Railway to access your GitHub if asked.

---

## Step 3: Create a new project

1. On the Railway dashboard, click **New Project** (or **Start a New Project**).
2. Choose **Deploy from GitHub repo**.
3. If this is your first time, click **Configure GitHub App** and allow Railway access to your repositories (or select **All repositories** / **Nitya-Dharma/Nitya_Dharma_project**).
4. Select the repo: **Nitya-Dharma/Nitya_Dharma_project**.
5. Click **Deploy Now** (or **Add Service**). Railway will create a new service from the repo.

---

## Step 4: Add PostgreSQL database

1. Inside your project, click **+ New** (or **Add Service**).
2. Select **Database** → **PostgreSQL**.
3. Railway will create a PostgreSQL service and automatically set **DATABASE_URL** for services in the same project (you can link it in the next step if needed).
4. Wait until the database shows **Active** or **Running**.

---

## Step 5: Link database to your web service

1. Click your **Web Service** (the one from GitHub, not the database).
2. Go to the **Variables** tab (or **Settings** → **Variables**).
3. If **DATABASE_URL** is not there yet:
   - Click **+ New Variable** or **Add Variable**.
   - Click **Add a reference** (or **Reference**).
   - Choose your **PostgreSQL** service.
   - Select the variable **DATABASE_URL**.
   - This adds a reference so your app gets the DB URL automatically.
4. If Railway already added **DATABASE_URL** when you created the DB in the same project, you may not need to do anything.

---

## Step 6: Set environment variables

Still in your **Web Service** → **Variables**:

Add (or confirm) these variables:

| Variable | Value |
|----------|--------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` |
| `SECRET_KEY` | Your secret key (same as in .env / Render / Vercel) |
| `DEBUG` | `False` |

- **DATABASE_URL** should already be set by linking the PostgreSQL service (Step 5).
- Do **not** set **ALLOWED_HOSTS**; the app adds `.railway.app` when **RAILWAY_PUBLIC_DOMAIN** is set.

---

## Step 7: Configure build and start (if needed)

Railway usually detects Python and uses your **Procfile**. If your service has custom settings:

1. Open your **Web Service** → **Settings** (or the **Settings** tab).
2. **Build Command** (optional; Railway often runs this automatically):
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
3. **Start Command** (optional; Procfile is used by default):
   ```bash
   gunicorn nityadharma.wsgi --log-file -
   ```
   If Railway shows a different start command, replace it with the one above.

If there is a **Root Directory** option, leave it **empty** (your app is in the repo root).

---

## Step 8: Generate a public URL

1. Open your **Web Service** (not the database).
2. Go to **Settings** → **Networking** (or **Deployments** → **Settings**).
3. Under **Public Networking**, click **Generate Domain** (or **Add Domain**).
4. Railway will assign a URL like `your-service-name.up.railway.app`. Copy it.

---

## Step 9: Deploy and check logs

1. Railway will deploy automatically when you push to GitHub, or when you add/save variables.
2. To deploy manually: **Deployments** → **Redeploy** (or **Deploy**).
3. Open the **Deployments** tab, click the latest deployment, and check **Logs** for errors.
4. When the build finishes, open your **Railway URL** (e.g. `https://xxx.up.railway.app`).

---

## Step 10: Run migrations (first time)

Railway doesn’t give a browser-based Shell like Render. Use one of these:

### Option A – Railway CLI (recommended)

1. Install Railway CLI: [railway.app/help/cli](https://docs.railway.app/develop/cli)
2. In your project folder:
   ```bash
   railway login
   railway link
   ```
   (Choose your project and the **Web Service**.)
3. Run migrations:
   ```bash
   railway run python manage.py migrate
   railway run python manage.py createsuperuser
   ```

### Option B – Run migrations from your PC

1. In Railway dashboard: **PostgreSQL** service → **Variables** (or **Connect**) → copy **DATABASE_URL**.
2. On your PC, in the project folder:
   ```bash
   set DATABASE_URL=<paste full URL here>
   set DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
   python manage.py migrate
   python manage.py createsuperuser
   ```
   (On Mac/Linux use `export` instead of `set`.)

After migrations, refresh your Railway app URL; the app should load.

---

## Checklist

- [ ] Code pushed to GitHub (with Railway ALLOWED_HOSTS support in prod.py).
- [ ] New Railway project created from **Nitya-Dharma/Nitya_Dharma_project**.
- [ ] PostgreSQL added and **DATABASE_URL** linked to the Web Service.
- [ ] Env vars set: **DJANGO_SETTINGS_MODULE**, **SECRET_KEY**, **DEBUG**.
- [ ] Public domain generated for the Web Service.
- [ ] Migrations run (CLI or from PC with **DATABASE_URL**).
- [ ] App opens at `https://xxx.up.railway.app` without errors.

---

## Troubleshooting

- **DisallowedHost / 400:** Ensure prod.py adds `.railway.app` when **RAILWAY_PUBLIC_DOMAIN** is set (already done). Don’t set **ALLOWED_HOSTS** in Railway unless you include `.railway.app`.
- **Database errors:** Confirm **DATABASE_URL** is set (reference from PostgreSQL service) and migrations have been run.
- **Static files missing:** Build command should include `python manage.py collectstatic --noinput`; WhiteNoise will serve them.
- **Build fails:** Check **Logs** for the failing step; fix **requirements.txt** or env vars and redeploy.

Your app URL will be: **https://&lt;your-service-name&gt;.up.railway.app**
