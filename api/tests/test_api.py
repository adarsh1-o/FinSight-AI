import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_kpis():
    response = client.get("/api/kpis/")
    assert response.status_code == 200
    data = response.json()
    assert "total_transactions" in data
    assert "total_transaction_amount" in data
    assert "potential_anomalies" in data

def test_get_anomalies_summary():
    response = client.get("/api/anomalies/summary")
    assert response.status_code == 200
    data = response.json()
    assert "iqr_anomaly_count" in data
    assert "ml_anomaly_count" in data
    assert "overlap_count" in data
    assert "terminology_note" in data
    assert "fraud" not in data.get("terminology_note", "").lower() or "not confirmed fraud" in data.get("terminology_note", "").lower()

def test_get_segments_summary():
    response = client.get("/api/segments/summary")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_monthly_trends():
    response = client.get("/api/trends/monthly")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
def test_invalid_query_parameter():
    response = client.get("/api/transactions?limit=-1") # Limit should be >= 1
    assert response.status_code == 422 # Validation error
