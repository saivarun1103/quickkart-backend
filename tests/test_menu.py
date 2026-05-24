from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_menu():

    response = client.get("/api/login")

    assert response.status_code == 405