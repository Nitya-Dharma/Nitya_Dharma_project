# Load Data from Local Database to Railway Production

You can copy data from your local MySQL database to Railway in two main ways.

---

## Prerequisites

1. **Railway MySQL must be reachable from your PC**  
   - In Railway dashboard: open your **MySQL** service → **Settings** → **Networking** (or **Public Networking**).  
   - Enable **TCP Proxy** if it’s not already (Railway often enables it by default).  
   - Note the **public host** and **port** (e.g. `shuttle.proxy.rlwy.net` and `15140`).  
   - Note the MySQL **user**, **password**, and **database** from the MySQL service **Variables** (e.g. `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`).

2. **Local DB**  
   - Your local Django app should be using MySQL and have the data you want to copy.

---

## Option 1: Django dumpdata → loaddata (recommended for app data)

Good for master data, users, content, etc. You can exclude sessions, admin logs, and other noisy tables.

### Step 1: Export from local database

In your project folder, with your **local** `.env` / database (so Django uses your local MySQL):

```powershell
cd "c:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"

# Activate venv if you use one
# venv\Scripts\activate

# Export all app data (exclude sessions, contenttypes, and admin logs to avoid clutter)
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e sessions.Session -e admin.LogEntry -o data_export.json
```

- To export **everything** (including contenttypes and sessions):

  ```powershell
  python manage.py dumpdata --natural-foreign --natural-primary -o data_export_full.json
  ```

- To export **only specific apps** (e.g. masterdata and accounts):

  ```powershell
  python manage.py dumpdata masterdata accounts --natural-foreign --natural-primary -o data_export_master.json
  ```

Use one of the above; you’ll get a file like `data_export.json` or `data_export_full.json`.

### Step 2: Build Railway MySQL URL (for connecting from your PC)

You need the **public** MySQL URL (TCP Proxy), not the internal one.

- From MySQL service **Variables**: `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`.  
- From MySQL service **Networking**: TCP Proxy **host** and **port**.

URL format:

```text
mysql://MYSQLUSER:MYSQLPASSWORD@TCP_PROXY_HOST:TCP_PROXY_PORT/MYSQLDATABASE
```

Example (replace with your values):

```text
mysql://root:abc123@shuttle.proxy.rlwy.net:15140/railway
```

If the password has special characters, URL-encode them (e.g. `@` → `%40`, `#` → `%23`).

### Step 3: Load data into Railway from your PC

Point Django at Railway’s database and run `loaddata` **once** (this will add/update rows; be careful not to run multiple times if you don’t want duplicates):

```powershell
# PowerShell (one line)
$env:DATABASE_URL="mysql://root:YOUR_PASSWORD@TCP_PROXY_HOST:TCP_PROXY_PORT/railway"; $env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"; python manage.py loaddata data_export.json
```

Replace `DATABASE_URL` with your real Railway MySQL URL and `data_export.json` with the file you created. Use `data_export_full.json` if you exported everything.

- If you use **Command Prompt** (cmd):

  ```cmd
  set DATABASE_URL=mysql://root:YOUR_PASSWORD@TCP_PROXY_HOST:TCP_PROXY_PORT/railway
  set DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
  python manage.py loaddata data_export.json
  ```

Your local Django runs `loaddata` but writes to **Railway’s MySQL**, so all data from the fixture goes to production.

### Step 4: Clean up (optional)

- Delete the export file if it contains sensitive data and you don’t want it in the repo:

  ```powershell
  del data_export.json
  ```

- `data_export*.json` is in `.gitignore` (see below), so it won’t be committed by mistake.

---

## Option 2: Full MySQL dump and restore (exact copy)

This clones the whole database (all tables and data). Use it when you want an exact copy of local DB on Railway.

### Step 1: Dump local MySQL

From your PC (MySQL client must be installed):

```powershell
# Replace with your local DB name, user, and password
mysqldump -u YOUR_LOCAL_USER -p YOUR_LOCAL_DATABASE > backup.sql
```

Enter your local MySQL password when prompted. You’ll get `backup.sql`.

### Step 2: Get Railway MySQL TCP Proxy details

Same as in Option 1: MySQL service → **Variables** (user, password, database) and **Networking** (TCP Proxy host and port).

### Step 3: Import into Railway MySQL

```powershell
# Replace TCP_PROXY_HOST, TCP_PROXY_PORT, user, password, database
mysql -h TCP_PROXY_HOST -P TCP_PROXY_PORT -u MYSQLUSER -p MYSQLDATABASE < backup.sql
```

Enter Railway’s MySQL password when prompted. This replaces/overwrites data in Railway’s database with your dump.

**Warning:** This will overwrite existing data in Railway (including any users and content created only on Railway). Use only if you intend to replace the whole DB.

---

## Notes

- **Passwords:** Never commit `data_export.json`, `backup.sql`, or `.env` to Git. Add them to `.gitignore` (e.g. `data_export*.json`, `backup.sql`).
- **Users and passwords:** If you dump auth users, the same user accounts (and hashed passwords) will exist on Railway. Change important passwords after load if needed.
- **Media files:** Dumpdata/loaddata and MySQL dump only copy **database** data. Uploaded files (e.g. in `media/`) are not in the DB. To get the same logo/files on Railway you must either re-upload them or use persistent storage (e.g. Volume/S3) and copy files separately.
- **Railway egress:** Using TCP Proxy from your PC counts as egress; typically small for one-time imports.

---

## Quick reference (Option 1)

1. Export local: `python manage.py dumpdata ... -o data_export.json`  
2. Get Railway MySQL URL (TCP Proxy host, port, user, password, database).  
3. Set `DATABASE_URL` and `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`, then run: `python manage.py loaddata data_export.json`  
4. Optionally remove `data_export.json` and never commit it.
