import os
import importlib


def test_sqlite_created(tmp_path, monkeypatch):
  db_path = tmp_path / "app.db"
  monkeypatch.setenv("SQLITE_PATH", str(db_path))

  if "backend.app.main" in importlib.sys.modules:
    importlib.reload(importlib.import_module("backend.app.main"))
  else:
    importlib.import_module("backend.app.main")

  assert db_path.exists()


