# Best and Safest Way: Load Local DB Data to Railway (Detailed Steps)

**Recommended method:** Django **dumpdata** (export from local) → **loaddata** (import into Railway).  
This is the safest because:
- You export to a file first and can check it.
- You control what is excluded (sessions, admin logs).
- You run loaddata once with Railway’s URL, so you don’t overwrite your local DB.
- No raw SQL; Django handles models and relations.

---

## Before you start

- **Local:** Django uses your **local MySQL** (e.g. via `.env` or `DB_*` / `MYSQL_URL`).
- **Railway:** MySQL service is running; **TCP Proxy** is enabled so you can connect from your PC.
- **Time:** First time about 10–15 minutes; repeat when you want to refresh Railway from local.

---

## Step 1: Confirm you’re on local DB and have data

1. Open terminal in your project folder:
   ```powershell
   cd "c:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"
   ```
2. Activate virtualenv if you use one:
   ```powershell
   venv\Scripts\activate
   ```
3. (Optional) Confirm Django is using local DB:
   ```powershell
   python manage.py check_db_connection
   ```
   You should see **DB host: localhost** (or your local MySQL host). If you see a Railway host, your `.env` might be pointing at Railway; fix that so export reads from local.

4. Make sure the data you want (users, poojas, pages, etc.) exists in your local app (e.g. log in locally, check admin).

---

## Step 2: Export from local (dumpdata) – safe, read‑only

This only **reads** from your local database and writes a **file**. It does not touch Railway.

1. Run one of these (choose one).

   **A) Recommended – all important data, exclude sessions and admin logs:**
   ```powershell
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e sessions.Session -e admin.LogEntry -o data_export.json
   ```

   **B) Everything (including contenttypes and sessions):**
   ```powershell
   python manage.py dumpdata --natural-foreign --natural-primary -o data_export_full.json
   ```

   **C) Only specific apps (e.g. masterdata + accounts):**
   ```powershell
   python manage.py dumpdata masterdata accounts --natural-foreign --natural-primary -o data_export_master.json
   ```

2. Wait until it finishes. You should see a file in the project folder:
   - `data_export.json` (option A)
   - or `data_export_full.json` (option B)
   - or `data_export_master.json` (option C)

3. Check the file size (e.g. in Explorer or `dir data_export.json`). It should not be empty.  
   **Do not commit this file** (it’s in `.gitignore`; it may contain sensitive data).

---

## Step 3: Get Railway MySQL connection details (TCP Proxy)

You need the **public** connection so your PC can reach Railway’s MySQL.

1. Go to **https://railway.app** → your project.
2. Click the **MySQL** service (not the web service).
3. Open the **Variables** tab. Note:
   - `MYSQLUSER`
   - `MYSQLPASSWORD`
   - `MYSQLDATABASE`
4. Open **Settings** (or **Networking** / **Public Networking**).
5. Find **TCP Proxy**. If it’s off, turn it **on**.
6. Note the **public host** and **port** (e.g. `something.proxy.rlwy.net`, `15140`).

Build the URL:

```text
mysql://<username>:<password>@<host>/<database>
```

Use your Railway Variables (MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE) and TCP Proxy host:port for &lt;host&gt;. **Never commit the real URL or password to Git.**

**Important:** If the password has special characters, URL‑encode them in the URL:

| Character | Use in URL |
|-----------|------------|
| `@`       | `%40`      |
| `#`       | `%23`      |
| `%`       | `%25`      |
| `&`       | `%26`      |
| `=`       | `%3D`      |
| `?`       | `%3F`      |

Write this URL down somewhere temporary (or keep the Variables tab open). You’ll use it only in the next step.

---

## Step 4: Point Django at Railway and load data (loaddata)

In this step, Django will connect to **Railway’s MySQL** and load the file you created. Your **local** database is not modified.

1. Stay in the same terminal and project folder.
2. Set the **Railway** MySQL URL. Your project’s prod settings use **MYSQL_URL** when present, so set that (or **DATABASE_URL** if you use it for MySQL):

   **PowerShell – set MYSQL_URL (recommended for your project):**
   ```powershell
   $env:MYSQL_URL="mysql://<username>:<password>@<host>/<database>"
   ```
   Replace the whole URL with the one you built in Step 3.

   **PowerShell – alternative (if your prod uses DATABASE_URL for MySQL):**
   ```powershell
   $env:DATABASE_URL="mysql://<username>:<password>@<host>/<database>"
   ```

3. Set production settings so Django uses prod DB config:
   ```powershell
   $env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"
   ```

4. **Verify you’re about to write to Railway (optional but safe):**
   ```powershell
   python manage.py check_db_connection
   ```
   You should see **DB host:** the TCP proxy host (e.g. `*.proxy.rlwy.net`) or similar, and **Connected to Railway database.** If you still see **localhost**, stop and fix the URL / variable name.

5. Run loaddata **once** (use the same filename you created in Step 2):
   ```powershell
   python manage.py loaddata data_export.json
   ```
   Or:
   ```powershell
   python manage.py loaddata data_export_full.json
   ```
   Or:
   ```powershell
   python manage.py loaddata data_export_master.json
   ```

6. Wait until it finishes. You should see lines like “Installed 1234 object(s)”.  
   - If you see **IntegrityError** or duplicate key errors, you may have run loaddata on Railway before; the data might already be there. You can fix conflicts or re‑export from local and try again (sometimes excluding already-loaded apps).
   - If you see **OperationalError** (e.g. can’t connect), check TCP Proxy, URL, and password encoding.

7. After a successful run, **unset** the URL so your next commands don’t accidentally use Railway:
   ```powershell
   Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
   Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
   $env:DJANGO_SETTINGS_MODULE=""
   ```
   Or close the terminal and open a new one for normal local work.

---

## Step 5: Verify on Railway

1. Open your Railway app in the browser (e.g. `https://web-production-7256f4.up.railway.app`).
2. Log in with a user that existed in your local DB (same email/password as locally).
3. Check that the data you expect is there: poojas, pages, master data, etc.

If you see your data, the load was successful.

---

## Step 6: Clean up (recommended for safety)

1. Delete the export file so it’s not left on disk with sensitive data:
   ```powershell
   del data_export.json
   ```
   (or `data_export_full.json` / `data_export_master.json` if you used those names.)

2. Confirm it’s not tracked by Git (it should be ignored):
   ```powershell
   git status
   ```
   You should **not** see `data_export.json` (or the other names) in the list.  
   `data_export*.json` is in `.gitignore`, so it won’t be committed by mistake.

---

## Safety summary

| What | Why it’s safe |
|------|-------------------------------|
| Export (Step 2) | Only reads from local DB; writes a file. Does not touch Railway. |
| Load (Step 4) | You explicitly set Railway’s URL and run loaddata once. Local DB not used. |
| check_db_connection (Step 4) | Confirms Django is connected to Railway before loaddata. |
| Excluding sessions/admin (Step 2) | Keeps fixture smaller and avoids loading temporary/admin clutter. |
| Deleting export file (Step 6) | Reduces risk of leaking sensitive data. |
| .gitignore | Prevents committing the export file. |

---

## If something goes wrong

- **“Unknown database” or connection refused**  
  Check TCP Proxy is on, and that host/port/user/password/database in the URL are correct. Password special characters must be URL‑encoded.

- **Duplicate key / IntegrityError on loaddata**  
  Some records may already exist on Railway. You can: (1) use a fixture that excludes those apps, or (2) clear Railway’s DB and run loaddata again (only if you’re okay replacing all Railway data).

- **Export file is empty or very small**  
  Make sure Django was using your local DB when you ran dumpdata (check_db_connection before export).

- **After load, Railway site still looks empty**  
  Hard-refresh the page (Ctrl+F5), try another browser or incognito, and confirm you’re logging in with a user that was in the exported data.

---

## Quick checklist

- [ ] Export from local: `python manage.py dumpdata ... -o data_export.json`
- [ ] Get Railway MySQL URL (Variables + TCP Proxy host/port)
- [ ] Encode password special characters in the URL
- [ ] Set `MYSQL_URL` (or `DATABASE_URL`) and `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`
- [ ] Run `python manage.py check_db_connection` → must show Railway
- [ ] Run `python manage.py loaddata data_export.json` once
- [ ] Unset env vars (or new terminal)
- [ ] Verify on Railway in browser
- [ ] Delete `data_export.json`

This is the best and safest way to get all the data you added on localhost into Railway.
