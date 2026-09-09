import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# On Vercel the SQLite file lives in /tmp of a fresh lambda, so the tables created by
# build_files.sh at build time are not there at request time. Apply migrations once per
# cold start (a few ms for one small table). Failure here must not take the API down.
if os.environ.get("VERCEL"):
    try:
        from django.core.management import call_command

        call_command("migrate", interactive=False, verbosity=0)
    except Exception:  # pragma: no cover - best effort; views also tolerate a missing table
        pass

app = application  # Vercel's Python runtime looks for `app`
