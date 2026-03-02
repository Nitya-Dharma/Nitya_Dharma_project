# Deploy Nitya Dharma to Render

## 1. Push latest code to GitHub

Make sure all changes (including `Procfile`, `requirements.txt`, and settings updates) are committed and pushed to:

`https://github.com/Nitya-Dharma/Nitya_Dharma_project`

---

## 2. Create a PostgreSQL database on Render (recommended)

1. In Render Dashboard: **New** → **PostgreSQL**.
2. Name it (e.g. `nityadharma-db`), choose region **Oregon (US West)** (same as your web service).
3. Create. Render will set **DATABASE_URL** automatically when you link it to the web service.

---

## 3. New Web Service – form values

Connect the repo **Nitya-Dharma/Nitya_Dharma_project** and use:

| Field | Value |
|-------|--------|
| **Name** | `nity-dharma-app` (or any name you like) |
| **Region** | Oregon (US West) |
| **Root Directory** | *Leave empty* |
| **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| **Start Command** | `gunicorn nityadharma.wsgi --log-file -` |
| **Instance Type** | Free (or paid if you prefer) |

---

## 4. Environment variables (required)

In the same **New Web Service** page, open **Advanced** → **Environment Variables**. Add:

| Key | Value | Notes |
|-----|--------|--------|
| `DJANGO_SETTINGS_MODULE` | `nityadharma.settings.prod` | **Required** – use production settings |
| `SECRET_KEY` | *(generate a long random string)* | e.g. from [djecrety.ir](https://djecrety.ir/) or `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | Never use True in production |
| `ALLOWED_HOSTS` | `.onrender.com` | Or leave empty; Render host is added automatically |

**If you created a PostgreSQL database (step 2):**

- In the web service, go to **Environment** → **Link existing resource** and link the PostgreSQL database. That will add **DATABASE_URL** automatically. No need to set MySQL vars.

**If you are not using a database on Render** (e.g. external MySQL):

- Add: `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` as in your current production setup.

---

## 5. Create Web Service

Click **Create Web Service**. Render will:

1. Clone the repo  
2. Run the build command (install deps + collectstatic)  
3. Start the app with gunicorn  

---

## 6. Run migrations (first deploy)

After the first successful deploy:

1. Open your service → **Shell** tab.
2. Run:
   ```bash
   python manage.py migrate
   ```
3. (Optional) Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

---

## 7. After-push checklist

- [ ] Code pushed to GitHub (including `Procfile`, updated `requirements.txt`, settings).
- [ ] PostgreSQL created and linked (or MySQL env vars set).
- [ ] `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod` set.
- [ ] `SECRET_KEY` set (random, secret).
- [ ] `DEBUG=False`.
- [ ] Migrations run in Render Shell.

Your app URL will be: `https://<your-service-name>.onrender.com`
