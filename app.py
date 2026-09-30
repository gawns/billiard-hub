"""Entrypoint untuk deploy Vercel (zero-config Flask).

Seluruh logika & route tetap berada di myapp.py (satu sumber kebenaran).
Vercel mencari instance Flask bernama `app` di app.py pada root proyek.
"""
from myapp import app  # noqa: F401  (dibaca Vercel sebagai WSGI handler)
