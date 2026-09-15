# Deploy Nitya Dharma on Hostinger KVM2 VPS

This guide is the **primary** production path for **Hostinger KVM2** (2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB bandwidth): bare-metal Nginx → Gunicorn (systemd) → Django `nityadharma.settings.prod` → MySQL on localhost.

**Not covered by this guide (separate paths):**

- **Docker Compose** — additive stack; see `docker-compose.yml` / `.env.example` (Batch 1 defaults Compose to prod settings).
- **Procfile / PaaS** (Railway, etc.) — uses `gunicorn.conf.py`; set `DJANGO_SETTINGS_MODULE` on the platform. Do not mix with this VPS procedure.

Gunicorn, logging, and Nginx below are tuned for the Hostinger KVM2 plan.

---

## 0. Deployment safety (read before migrating)

### First-launch architecture (Option A)

This Hostinger path is intentionally:

**Nginx → Gunicorn (systemd) → Django `nityadharma.settings.prod` → MySQL**

**without** requiring Redis or Celery for the first launch. Do not enable Redis/Celery casually (see §4).

### Database safety — never use production DBs for testing

- The original live database name documented for Hostinger is `nityadharma_db`. It is **protected production data**. **Never** use it for testing, QA, fixtures, browser experiments, Django shell experiments, ORM experiments, or migration experiments.
- **Never** use `nityadharma_recovery_20260817` for testing or experiments.
- Automated testing must use the dedicated database **`test_nityadharma_db`** only (separate controlled test phase — not this deploy guide).
- Do **not** use a live or recovery database as a test database.
- Do **not** run global migrations as a testing technique.
- Production migration is a **separate controlled operation** requiring explicit approval after preflight and backup gates (see §5).

### Backup ≠ restore ≠ migration

- A **backup** is not the same as a **restore drill**.
- A backup file existing is **not** proof of recoverability.
- Restore drills must use a **safe non-production** target. Never experiment with restore against the original live DB.
- This guide does **not** claim that backup or restore has already been performed on your VPS. Those gates must be completed and verified before any production migration.

### Host-only items (REQUIRES REAL VPS VERIFICATION)

Repository templates and this document are **not** proof that the live VPS is configured. Always verify on the host:

DNS · HTTPS/Certbot · live Nginx · live Gunicorn/systemd · actual `.env` presence · MySQL identity · filesystem permissions · backup location/disk space · log paths.

### Approved production process (do not use bare development defaults)

On Hostinger, start the app via:

- **systemd** unit `deployment/gunicorn.service` (sets `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`, loads `.env`, runs `gunicorn … --config gunicorn_config.py`), or
- Manual smoke: `gunicorn nityadharma.wsgi:application --config gunicorn_config.py` with prod settings exported (see §6–§7).

Bare `nityadharma.wsgi` without that config/env can fall back to **development** settings defaults. Do **not** run production that way. (PaaS/Procfile uses `gunicorn.conf.py` separately; do not mix with this VPS procedure.)

---

## 1. Server setup

SSH into your VPS and update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install Python, Nginx, MySQL, and Git:

```bash
sudo apt install -y python3-pip python3-venv python3-dev nginx mysql-server git build-essential libmysqlclient-dev pkg-config
```

---

## 2. MySQL

Create a database and user:

```bash
sudo mysql -e "CREATE DATABASE nityadharma_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'nityadharma_user'@'localhost' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';"
sudo mysql -e "GRANT ALL PRIVILEGES ON nityadharma_db.* TO 'nityadharma_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

Use your own strong password. Do not commit it. Put the same value in `.env` as `DATABASE_PASSWORD`.

---

## 3. Project directory and virtual environment

```bash
sudo mkdir -p /var/www/nityadharma
sudo chown $USER:$USER /var/www/nityadharma
cd /var/www/nityadharma
git clone https://github.com/YOUR_ORG/nityadharma.git .
# Or upload via SFTP / rsync
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Ownership for systemd (`User=www-data`)

`deployment/gunicorn.service` runs Gunicorn as **`www-data`**. After install/setup as your SSH user, grant that account access (adjust only what is needed; do not invent a new service user):

```bash
# Readable app + venv for the service user
sudo chown -R www-data:www-data /var/www/nityadharma
# Or keep deployer ownership and use group/ACL; minimum: www-data must read code, venv, .env and write logs/ + media/
```

If you prefer to keep the tree owned by your deploy user, you must still ensure `www-data` can execute the venv Gunicorn binary and read `.env`. Changing `User=` in the unit is a separate ops decision — this repository’s service file uses `www-data`.

---

## 4. Environment variables

Copy the example env file and edit with your values (no secrets in code):

```bash
cp .env.example .env
nano .env
```

Never commit `.env`. systemd loads it via `EnvironmentFile=/var/www/nityadharma/.env` in `deployment/gunicorn.service`.

Set at least:

- `SECRET_KEY` (long random string) — **required** by prod settings
- `DEBUG=False` (prod also hardcodes `DEBUG = False`)
- `SITE_URL=https://yourdomain.com`
- `DATABASE_NAME=nityadharma_db`
- `DATABASE_USER=nityadharma_user`
- `DATABASE_PASSWORD=...` (same as MySQL user password)
- `DATABASE_HOST=localhost`
- `DATABASE_PORT=3306`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- `SECURE_SSL_REDIRECT=True` after TLS is live (default in prod is True)
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (see below) — set explicitly for your production domain(s)

### Hosts / CSRF (current prod behavior — important)

`nityadharma.settings.prod` reads **`ALLOWED_HOSTS`** and **`CSRF_TRUSTED_ORIGINS`** from the environment (comma-separated; see `.env.example`).

- If unset or empty after parsing, prod falls back to secure defaults: `nityadharma.com`, `www.nityadharma.com` and matching `https://…` CSRF origins.
- Operators **should** set these explicitly in `/var/www/nityadharma/.env` to match the live domain(s) and Nginx `server_name`.
- Do **not** use `ALLOWED_HOSTS=*` or empty allowlists.
- Do **not** put insecure `http://` origins in `CSRF_TRUSTED_ORIGINS` for production HTTPS sites.
- Setting these in `.env` **does** apply when using `nityadharma.settings.prod` (via python-decouple).

### Logging directory

Prod settings read `LOG_DIR` from the environment (default in code is `/logs`, which suits Docker).
For Hostinger, the systemd unit sets:

```ini
Environment="LOG_DIR=/var/www/nityadharma/logs"
```

Create the directory and ensure `www-data` can write it:

```bash
mkdir -p /var/www/nityadharma/logs
sudo chown www-data:www-data /var/www/nityadharma/logs
```

Do not change `prod.py` for Hostinger logging; set `LOG_DIR` via systemd (already in the unit) or `.env` if you override it.

### Redis / Celery (optional — not required for Option A)

This Hostinger guide does **not** install or manage Redis or Celery. There is no `celery.service` in `deployment/`. Async workers are part of the **Docker Compose** path unless you add a separate ops unit later.

- Redis is **optional**. Without `REDIS_URL`, Django uses LocMem cache (and DB sessions when Redis is unset).
- **Do not set `REDIS_URL` casually.** In application settings, if `CELERY_BROKER_URL` is unset, Celery’s broker falls back to `REDIS_URL` (then to a localhost Redis default). Enabling Redis without an operating Celery worker can leave queued tasks (for example email) **unprocessed** while looking successful to the web request.
- Redis + Celery (separate broker URL such as Redis DB `/2`, plus a worker) is a **separate future operational phase**, not part of first Hostinger launch Option A.
- Leave `REDIS_URL` unset for Option A unless you intentionally deploy and operate Celery with an explicit `CELERY_BROKER_URL`.

---

## 5. Static files and conditional migrations

### 5.1 Collect static (safe after code deploy)

Ensure logs exist (see §4), then:

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
export LOG_DIR=/var/www/nityadharma/logs
python manage.py collectstatic --noinput
```

### 5.2 Pre-migration safety gates (required before any production migrate)

**Do not** treat “migration files exist in Git” as an automatic instruction to run `migrate`.

Unapplied migrations in the repository **do not** mean you must migrate immediately. Migration is **conditional** on preflight, backup/restore readiness, and **explicit approval**.

Complete these gates **before** any production `migrate`:

1. Confirm the intended release/commit SHA on the VPS.
2. Confirm the application directory (`/var/www/nityadharma` or your approved path).
3. Confirm the virtualenv (`venv`) and that it is activated for manage commands.
4. Confirm production env: `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod` and a readable `.env` (do not commit secrets).
5. Confirm the **correct production database identity** (name/host as configured — do not guess; do not point tools at recovery or test DBs by mistake).
6. Confirm a **fresh production database backup** has been created under your approved backup procedure.
7. Confirm the backup is usable / integrity-checked (size, checksum, and/or equivalent verification).
8. Confirm a **recovery/restore path** exists (a restore drill in a **non-production** environment is required for confidence; never practice restore against the live DB).
9. Perform the separately authorized **read-only** production migration/schema preflight.
10. Determine the **actual** migration delta (what is already applied vs what the release expects).
11. Review high-risk migration prerequisites (for example additive User fields, unique constraints, data `RunPython` migrations) with an approved operator/DBA checklist.
12. Explicit **GO / NO-GO** decision.
13. **Only if** migration is required **and** explicit deployment/migration approval exists, proceed with a controlled migration procedure.

If any gate fails: **STOP**. Do not migrate. Do not use production as a testing environment.

### 5.3 Controlled migration (only after GO)

When — and only when — the gates above pass and approval is recorded:

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
export LOG_DIR=/var/www/nityadharma/logs
# ONLY after preflight + backup + restore readiness + explicit approval:
python manage.py migrate
```

Never run migrate against `nityadharma_recovery_20260817`, never use migrate to “test”, and never run global migrations as a substitute for proper preflight.

---

## 6. Smoke-test Gunicorn (approved config)

Use the Hostinger Gunicorn config file (**`gunicorn_config.py`**), not a bare WSGI invoke:

```bash
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
export LOG_DIR=/var/www/nityadharma/logs
gunicorn nityadharma.wsgi:application --config gunicorn_config.py
```

In another terminal: `curl http://127.0.0.1:8000/`. Then stop Gunicorn (Ctrl+C).
---

## 7. systemd service for Gunicorn

Use the project’s service file (paths assume app at `/var/www/nityadharma`):

```bash
sudo cp deployment/gunicorn.service /etc/systemd/system/
# If your app lives elsewhere, edit paths in the service file:
# sudo nano /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

The unit already:

- sets `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`
- sets `LOG_DIR=/var/www/nityadharma/logs`
- loads `EnvironmentFile=/var/www/nityadharma/.env`
- runs as `User=www-data` / `Group=www-data`
- starts: `gunicorn nityadharma.wsgi:application --config gunicorn_config.py`

If the service fails on start, confirm `.env` exists at `/var/www/nityadharma/.env` and is readable by `www-data`.

After editing `.env` or the unit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

---

## 8. Nginx reverse proxy

The repository ships an **HTTP (port 80) template** for initial setup. HTTPS is **not** active in the template until you obtain certificates on the VPS.

Copy and enable the Nginx config (replace `yourdomain.com` with your domain **on the server**, not by committing secrets/domains into git):

```bash
sudo cp deployment/nginx_hostinger.conf /etc/nginx/sites-available/nityadharma
sudo sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/nityadharma
sudo ln -s /etc/nginx/sites-available/nityadharma /etc/nginx/sites-enabled/
# Remove default site if it conflicts:
# sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Ensure Nginx (`www-data`) can read static and media:

```bash
sudo chown -R www-data:www-data /var/www/nityadharma/staticfiles /var/www/nityadharma/media
```

Upstream is `127.0.0.1:8000` (Gunicorn). Proxy sets `X-Forwarded-Proto $scheme` for Django `SECURE_PROXY_SSL_HEADER`.

---

## 9. SSL with Let’s Encrypt (Certbot) — VPS operations step

**Repository state:** `deployment/nginx_hostinger.conf` starts as HTTP-only. The HTTPS server block in that file is a **commented example**. Shipping the repo does **not** mean TLS is live.

On the VPS, after DNS points to the server:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Typical sequence:

1. HTTP template works for initial reachability / ACME challenges.
2. Point DNS A/AAAA records at the VPS.
3. Run Certbot; it obtains certificates and adjusts Nginx for HTTPS.
4. Prefer Certbot-managed HTTPS over manually uncommenting the sample block with incomplete paths.
5. After TLS is actually active, enable HTTP → HTTPS redirect (Certbot option and/or the commented `return 301` in the HTTP server).
6. Keep Django `SECURE_SSL_REDIRECT=True` (prod default) so redirects/cookies align once the proxy sends `X-Forwarded-Proto: https`.

Renewal check:

```bash
sudo certbot renew --dry-run
```

Do not commit real certificate files or private keys into the repository.

---

## 10. Security checklist

- **Secrets:** In `.env` loaded by systemd `EnvironmentFile`; never in git.
- **DEBUG:** `False` in `nityadharma.settings.prod`.
- **Hosts / CSRF:** Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `.env` to match live domains (env-driven in prod; secure defaults if unset — see §4). No wildcards; no insecure HTTP CSRF origins in production.
- **HTTPS:** Only after Certbot on the VPS; do not treat the repo template as TLS-complete. **REQUIRES REAL VPS VERIFICATION.**
- **Entrypoint:** Use systemd + `gunicorn_config.py` (or the §6 smoke command). Do not run bare WSGI under development defaults in production.
- **Redis:** Leave unset for Option A unless Celery is intentionally operated (see §4).
- **Firewall:** `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`.
- **Testing:** Never use `nityadharma_db` or `nityadharma_recovery_20260817` for testing; automated tests use `test_nityadharma_db` only.
---

## 11. Useful commands

| Task              | Command |
|-------------------|--------|
| Gunicorn status   | `sudo systemctl status gunicorn` |
| Gunicorn logs     | `journalctl -u gunicorn -f` |
| Django app logs  | `tail -f /var/www/nityadharma/logs/django.log` |
| Nginx test        | `sudo nginx -t` |
| Nginx reload      | `sudo systemctl reload nginx` |
| Restart app       | `sudo systemctl restart gunicorn` |

---

## 12. VPS specs (KVM2)

Configurations used for this plan:

- **Gunicorn:** 3 workers, sync, timeout 120s, bind `127.0.0.1:8000` (see `gunicorn_config.py`).
- **Logging:** `LOG_DIR=/var/www/nityadharma/logs` via systemd; rotating files (10 MB × 5 backups).
- **Static/Media:** Served by Nginx from `staticfiles/` and `media/` on NVMe; WhiteNoise still available if needed.
- **Database:** MySQL via `DATABASE_*` (or `DB_*`) env vars; no credentials in code.
- **Email:** SMTP via `EMAIL_*` env vars; no credentials in code.
- **Celery / Redis:** Not managed by this Hostinger systemd path (Option A). Treat Redis+Celery as a separate future ops phase.

After deployment, run `git status` and `git diff` before committing any changes; never commit `.env` or secrets.
