# -*- coding: utf-8 -*-
"""Prueba de humo: la app completa (las dos pestanas) renderiza sin excepciones.  python test_app.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from streamlit.testing.v1 import AppTest  # noqa: E402

t0 = time.time()
at = AppTest.from_file("app.py", default_timeout=180)
at.secrets["PASSWORD"] = ""
at.run()
errs = [e.value for e in at.exception] + [e.value for e in at.error]
print(f"app {time.time() - t0:5.1f}s  {'ok' if not errs else 'ERROR ' + str(errs[0])[:900]}")
print("warnings:", [w.value[:80] for w in at.warning])
sys.exit(bool(errs))
