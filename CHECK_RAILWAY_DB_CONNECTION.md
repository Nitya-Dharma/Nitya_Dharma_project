# How to Check If Railway Is Using the Railway Database

## Why you don't see your local data on Railway

Your **local** app uses your **local MySQL** (e.g. on your PC).  
Your **Railway** app uses **Railway’s MySQL** (a separate database in the cloud).

They are **two different databases**. Data you add on localhost stays in your local DB. It does **not** automatically appear on Railway. So “details stored in localhost” will never show on the Railway deployment until you **load that data into Railway’s database**.

---

## 1. Confirm the web app is using Railway’s database

### A. Check variables in Railway

1. Go to [railway.app](https://railway.app) → your project.
2. Click the **web** service (not MySQL).
3. Open **Variables** (or **Settings** → **Variables**).
4. You should see **MYSQL_URL** (or **DATABASE_URL** if you use Postgres).
   - If **MYSQL_URL** is set (and no **DATABASE_URL**), the app uses **Railway’s MySQL**.
   - The value will look like: `mysql://<username>:<password>@mysql.railway.internal:3306/<database>` (internal) or use a TCP proxy host if set.

If **MYSQL_URL** is missing on the web service, the app cannot use Railway’s MySQL. Add it by referencing the MySQL service’s **MYSQL_URL** (or copy the value from the MySQL service Variables).

### B. Run a command on Railway (see which DB is used)

From your project folder, with Railway CLI linked to the **web** service, run:

```powershell
railway ssh -- python manage.py check_db_connection
```

(This uses a small management command in the project—no shell quoting issues.)

- If the app is using Railway’s MySQL you’ll see something like:
  - **DB host:** `mysql.railway.internal` (or the TCP proxy host)
  - **DB name:** the Railway MySQL database name (e.g. `railway`)
  - **Connected to Railway database.**
- If you see **DB host: localhost** and **DB name: your_local_db**, then the app is **not** using Railway’s database (e.g. wrong env or running locally).

So: **if the output shows Railway’s host and DB name, the database is connected**; the reason you don’t see local data is that this DB is separate and empty until you load data.

---

## 2. Quick test: create data on Railway and see it in the app

1. Create a superuser (or any record) **on Railway**:
   ```powershell
   railway ssh -- env DJANGO_SUPERUSER_PASSWORD=TestPass123 python manage.py createsuperuser --noinput --email test@example.com
   ```
2. Open your Railway site and log in with that email/password (e.g. at `/admin/`).
3. If you can log in, the app is **connected to Railway’s database** and is reading/writing there. The fact that you don’t see “details stored in localhost” is because that data is only in your **local** DB.

---

## 3. To see your local data on the Railway deployment

You have to **copy data from your local DB into Railway’s DB** (they are not the same):

1. Export from local: e.g. `python manage.py dumpdata ... -o data_export.json` (see **LOAD_DATA_TO_RAILWAY.md**).
2. Import into Railway’s DB (from your PC, pointing at Railway’s MySQL URL), e.g.:
   ```powershell
   $env:DATABASE_URL="mysql://<username>:<password>@<host>/<database>"   # Railway MySQL URL (TCP Proxy); never commit real URL
   $env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"
   python manage.py loaddata data_export.json
   ```
   Or use the full steps in **LOAD_DATA_TO_RAILWAY.md**.

After that, the “details you stored in localhost” will exist in Railway’s database and will show on the Railway deployment.

---

## Summary

| Question | Answer |
|----------|--------|
| Is Railway connected to a database? | Check **web** service **Variables** for **MYSQL_URL** (or **DATABASE_URL**). If set, the app uses that DB. |
| Which database is it? | Run the `railway ssh -- python manage.py shell -c "..."` command above; **DB host** and **DB name** tell you. |
| Why don’t I see my local data? | Because Railway uses **Railway’s MySQL**, not your local MySQL. Data is not shared. |
| How do I see my local data on Railway? | Load it into Railway’s DB using **LOAD_DATA_TO_RAILWAY.md** (dumpdata → loaddata or MySQL dump/restore). |
