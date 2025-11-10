from fastapi.testclient import TestClient
from rehab_admin_api.app import app
def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True
