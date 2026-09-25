import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_endpoint(path, params=None):
    resp = client.get(path, params=params)
    print(f"GET {path} params={params} -> {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2)[:500])
    except Exception:
        print(resp.text[:200])

# Health
test_endpoint("/health")
# KPIs
test_endpoint("/api/kpis/")
# Anomalies summary
test_endpoint("/api/anomalies/summary")
# Segments summary
test_endpoint("/api/segments/summary")
# Monthly trends
test_endpoint("/api/trends/monthly")
# With a filter example (date range if data permits)
# Assuming date format YYYY-MM-DD, using a wide range
test_endpoint("/api/kpis/", params={"date_from": "2000-01-01", "date_to": "2100-01-01"})
