"""Pytest bootstrap: make the backend importable and isolate the test database.

Setting OPENFPA_DATABASE_URL here (before any app import) ensures API tests use a throwaway
SQLite file instead of the developer's data/openfpa.db.
"""

import os
import tempfile
from pathlib import Path

sys_path_root = str(Path(__file__).resolve().parent)
import sys  # noqa: E402

if sys_path_root not in sys.path:
    sys.path.insert(0, sys_path_root)

_test_db = Path(tempfile.gettempdir()) / "openfpa_pytest.db"
for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(_test_db) + suffix)
    if candidate.exists():
        candidate.unlink()
os.environ.setdefault("OPENFPA_DATABASE_URL", f"sqlite:///{_test_db.as_posix()}")
# Keep the HTTP rate limiter off by default so the suite is deterministic; the dedicated
# security tests flip it back on locally via monkeypatch.
os.environ.setdefault("OPENFPA_RATE_LIMIT_ENABLED", "false")
