from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ingestion import ingest_csv

@pytest.fixture
def client_with_data(tmp_path, monkeypatch):
    db = tmp_path / "api_test.db"
    monkeypatch.setenv("DB_PATH", str(db))
    csv_path = Path(__file__).resolve().parents[1] / "data" / "sales_data.csv"
    ingest_csv(csv_path, str(db))
    with TestClient(app) as client:
        yield client

def test_health_endpoint(client_with_data):
    response = client_with_data.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ask_response_structure(client_with_data):
    response = client_with_data.post("/ask", json={"question": "What is the total revenue?"})
    assert response.status_code == 200
    payload = response.json()
    assert {"question", "intent", "answer", "result", "supporting_data", "query_method", "assumptions", "warnings"} <= set(payload)

def test_invalid_question_returns_client_error(client_with_data):
    response = client_with_data.post("/ask", json={"question": "Tell me the weather"})
    assert response.status_code == 400
