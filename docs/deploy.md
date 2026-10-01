# Deploy guide (Stage 6)

ScamPulse is a standard Django + WhiteNoise app, so any host that runs Python
over HTTPS works. **Pick a plan that does NOT idle-sleep during judging** —
free tiers that sleep add a cold-start delay that hurts the "under 10 seconds"
goal. Recommended: **Render Starter**, **Railway**, or **Fly.io** (check their
current limits before choosing).

## 1. Secrets (environment variables)
Never commit these; set them in the host dashboard.

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | a long random string |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | your host, e.g. `scampulse.onrender.com` |
| `DATABASE_URL` | *(optional)* a Postgres URL to switch off SQLite |

With `DEBUG=False` the app turns on **HSTS, secure cookies, SSL redirect and
content-type nosniff** automatically (see `config/settings.py`).

## 2. Render (one-click style)
This repo includes **`render.yaml`** and a **`Procfile`**. On Render:
1. New → Blueprint → point at the repo → it reads `render.yaml`.
2. Build runs `collectstatic`, `migrate`, `seed_feed`.
3. Start runs gunicorn. Health check hits **`/health`**.

Manual (any host): build = `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_feed`; start = `gunicorn config.wsgi --bind 0.0.0.0:$PORT`.

## 3. Create a moderator
```
python manage.py createsuperuser
```
Moderate at `/admin/` — filter by status/category/date, bulk **Approve**
(confirm) / **Reject**. Use a strong password; enable 2FA on the host account.

## 4. Service worker + offline
`/sw.js` is served from the site root with `Service-Worker-Allowed: /` and the
manifest from `/manifest.webmanifest`. HTTPS is required for installability and
the service worker — all the hosts above provide it. After deploy, run
Lighthouse (PWA + performance + accessibility) and test offline mode in
Chrome DevTools, then on two real Android phones (one low-end).

## 5. Updating the model
`python manage.py retrain` trains on the CSV + synthetic set + Confirmed
community reports, and **publishes only if neither the scams-wrongly-cleared
rate nor the false-alarm rate rises**; otherwise it keeps the current model and
logs why. Devices pick up the new `model.json` on their next poll.

## 6. Daily backup (SQLite)
If staying on SQLite, back up the single file daily:
`cp db.sqlite3 backups/db-$(date +%F).sqlite3`. For zero-maintenance, set
`DATABASE_URL` to a managed Postgres instead.
