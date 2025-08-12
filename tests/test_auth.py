import os
import importlib
from fastapi.testclient import TestClient


def bootstrap(db_path):
  os.environ["SQLITE_PATH"] = str(db_path)
  module_name = "backend.app.main"
  if module_name in importlib.sys.modules:
    importlib.reload(importlib.import_module(module_name))
  else:
    importlib.import_module(module_name)
  from backend.app.main import app
  return app


def test_create_and_login(tmp_path):
  app = bootstrap(tmp_path / "app.db")
  client = TestClient(app)

  # create user
  resp = client.post(
    "/api/users",
    json={
      "first_name": "Admin",
      "last_name": "User",
      "username": "admin",
      "email": "admin@example.com",
      "password": "secret",
      "is_super_admin": True,
    },
  )
  assert resp.status_code == 200, resp.text
  user = resp.json()
  assert user["is_super_admin"] is True

  # login
  resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret"})
  assert resp.status_code == 200, resp.text
  data = resp.json()
  assert data["email"] == "admin@example.com"


