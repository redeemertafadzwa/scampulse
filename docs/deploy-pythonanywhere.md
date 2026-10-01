# Deploy to PythonAnywhere (free, no sleep)

The free "Beginner" account runs one always-on web app at
`https://<username>.pythonanywhere.com` with HTTPS — good for judging.
The server only needs Django (detection runs on the phone), so we install the
slim `requirements-web.txt`.

## 1. Create the account
Sign up (free Beginner) at https://www.pythonanywhere.com. Note your **username** —
your site will be `https://<username>.pythonanywhere.com`.

## 2. Get the code on GitHub (public, so PythonAnywhere can clone it)
In GitHub Desktop: **Add local repository → `C:\Users\redee\Desktop\scampulse` →
Publish** (leave it **public**). You'll get a URL like
`https://github.com/<you>/scampulse.git`.

## 3. Clone it on PythonAnywhere
PythonAnywhere dashboard → **Consoles → Bash**, then:
```bash
git clone https://github.com/<you>/scampulse.git
cd scampulse
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-web.txt
python manage.py migrate
python manage.py seed_feed
python manage.py createsuperuser        # pick a strong password
python manage.py collectstatic --noinput
```

## 4. Create the web app
Dashboard → **Web → Add a new web app → Manual configuration → Python 3.11**.
Then on the Web tab set:

- **Source code:** `/home/<username>/scampulse`
- **Working directory:** `/home/<username>/scampulse`
- **Virtualenv:** `/home/<username>/scampulse/venv`

## 5. Edit the WSGI file
On the Web tab click the **WSGI configuration file** link and replace its
contents with:
```python
import os, sys
path = "/home/<username>/scampulse"
if path not in sys.path:
    sys.path.insert(0, path)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_SECRET_KEY"] = "paste-a-long-random-string-here"
os.environ["DJANGO_ALLOWED_HOSTS"] = "<username>.pythonanywhere.com"
os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = "https://<username>.pythonanywhere.com"
from config.wsgi import application
```

## 6. Reload
Click the big green **Reload** button. Visit
`https://<username>.pythonanywhere.com` — the app, `/admin/`, `/health`,
`/sw.js` and `/manifest.webmanifest` all work. WhiteNoise serves `/static/`.

## Keeping it alive
Free web apps ask you to click **"Run until 3 months from now"** every ~3 months —
do that before judging. It does **not** sleep between requests.

## Notes
- Static files are served by WhiteNoise from the app, so no static mapping is
  required. (You *may* add one on the Web tab for speed: URL `/static/` →
  `/home/<username>/scampulse/staticfiles`.)
- Retraining uses the full `requirements.txt` (scikit-learn/pandas) and is done
  **locally**, then commit the new `core/static/model.json` and `git pull` on
  PythonAnywhere + Reload.
