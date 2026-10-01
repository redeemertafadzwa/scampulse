# ScamPulse Zimbabwe

A mobile-first, installable PWA that helps people check a suspicious message,
understand why it's risky, and know what to do. The scam check runs **entirely
on the phone** (offline-capable); reporting is opt-in and redacted.

## Run it
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_feed          # clearly-marked example feed
python manage.py createsuperuser    # moderator for /admin/
python manage.py runserver
```
Open http://127.0.0.1:8000/ (admin at /admin/, health at /health).

## What's inside
- **On-device engine** — `normalise.py` + `engine.py` (rule signals + TF-IDF /
  logistic-regression, cautious voting). Mirrored in `core/static/js/` for the
  phone; **Python↔JS parity test**: `node tests/parity.test.js` (948 checks).
- **5 screens** — Check, Verdict (with "Why?" red-flag highlights), Community
  feed, Before-you-send checkpoint, Report. Settings: language, safe-word,
  privacy, delete-my-data. Bottom nav, 4 labelled icons.
- **Languages** — English (complete), chiShona (partial, reviewed), isiNdebele
  (starter) with English fallback; no silent machine translation. Voice read-out
  uses the browser's own voices.
- **Community** — opt-in redacted reports → fingerprint family matching →
  Confirmed after N devices or admin approval (Django admin, bulk approve/reject)
  → `python manage.py retrain` publishes a new model **only if metrics don't
  worsen**. Polling with ETag every 30s; works offline on the last model/feed.
- **PWA** — manifest + service worker + share_target, installable on Android.

## Tests
```bash
python -m pytest tests/test_core.py   # redaction never leaks, engine behaviour
node tests/parity.test.js             # Python/JS normalise parity
python ml/evaluate.py                 # detection metrics -> docs/evaluation-report.md
```

## Results (synthetic, held-out)
Test accuracy 100% · scams wrongly cleared 0% · false alarms 0% · disguised
caught 97.6%. See `docs/` (evaluation-report, known-limitations, credits, deploy).

## Deploy
See `docs/deploy.md` (Render/Railway/Fly; `render.yaml` + `Procfile` included).
Set `DEBUG=False` for HSTS/secure-cookies/SSL redirect.
