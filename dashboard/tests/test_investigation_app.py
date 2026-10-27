from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from dashboard import api_client


ROWS = [
    {"transaction_id": "t-1", "transaction_date": "2024-01-10T10:00:00", "customer_id": "c-1", "amount": 20,
     "transaction_type": "Purchase", "merchant_category": "Grocery", "payment_method": "Card", "status": "Completed",
     "isolation_prediction": -1, "isolation_score": -0.2, "ml_anomaly": 1, "synthetic_fraud_label": False},
    {"transaction_id": "t-2", "transaction_date": "2024-01-15T10:00:00", "customer_id": "c-2", "amount": 50,
     "transaction_type": "Purchase", "merchant_category": "Grocery", "payment_method": "Card", "status": "Completed",
     "isolation_prediction": 1, "isolation_score": 0.05, "ml_anomaly": 0, "synthetic_fraud_label": False},
    {"transaction_id": "t-3", "transaction_date": "2024-02-10T10:00:00", "customer_id": "c-3", "amount": 120,
     "transaction_type": "Purchase", "merchant_category": "Amazon", "payment_method": "Card", "status": "Completed",
     "isolation_prediction": -1, "isolation_score": -0.1, "ml_anomaly": 1, "synthetic_fraud_label": True},
    {"transaction_id": "t-4", "transaction_date": "2024-02-15T10:00:00", "customer_id": "c-4", "amount": 300,
     "transaction_type": "Purchase", "merchant_category": "Amazon", "payment_method": "Card", "status": "Completed",
     "isolation_prediction": 1, "isolation_score": 0.1, "ml_anomaly": 0, "synthetic_fraud_label": False},
]
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def filter_rows(params: dict) -> list[dict]:
    frame = pd.DataFrame(ROWS)
    if params.get("anomaly_status") == "flagged":
        frame = frame[frame.ml_anomaly == 1]
    elif params.get("anomaly_status") == "normal":
        frame = frame[frame.ml_anomaly == 0]
    if params.get("merchant_category"):
        frame = frame[frame.merchant_category == params["merchant_category"]]
    if params.get("transaction_id"):
        frame = frame[frame.transaction_id.str.contains(params["transaction_id"], case=False, regex=False)]
    if params.get("amount_min") is not None:
        frame = frame[frame.amount >= float(params["amount_min"])]
    if params.get("amount_max") is not None:
        frame = frame[frame.amount <= float(params["amount_max"])]
    if params.get("date_from"):
        frame = frame[frame.transaction_date.str[:10] >= params["date_from"]]
    if params.get("date_to"):
        frame = frame[frame.transaction_date.str[:10] <= params["date_to"]]
    return frame.sort_values("isolation_score").to_dict(orient="records")


def install_api_mocks(monkeypatch):
    investigation_calls: list[dict] = []
    export_calls: list[dict] = []
    downloaded_csv: list[bytes] = []

    def fetch_data(endpoint: str, params: dict | None = None):
        params = dict(params or {})
        if endpoint == "/date-range":
            return {"min_date": "2024-01-01", "max_date": "2024-02-28"}
        if endpoint == "/categories":
            return ["Amazon", "Grocery"]
        if endpoint in {"/payment-methods", "/locations", "/transaction-types", "/statuses"}:
            return {"/payment-methods": ["Card"], "/locations": ["Local"],
                    "/transaction-types": ["Purchase"], "/statuses": ["Completed"]}[endpoint]
        if endpoint == "/investigations":
            investigation_calls.append(params)
            items = filter_rows(params)
            return {"items": items, "total": len(items), "page": 1, "page_size": 500, "pages": int(bool(items)),
                    "score_note": "not a fraud probability"}
        if endpoint == "/transactions":
            return ROWS
        if endpoint == "/kpis/":
            return {"total_transactions": 4, "total_transaction_amount": 490, "average_transaction_amount": 122.5,
                    "unique_customers": 4, "potential_anomalies": 2, "anomaly_percentage": 50}
        if endpoint == "/trends/monthly":
            return [{"month": "2024-01", "transaction_count": 2, "transaction_amount": 70, "potential_anomalies": 1}]
        if endpoint == "/transactions/summary/categories":
            return [
                {"merchant_category": "Amazon", "transaction_count": 2, "total_amount": 420, "average_amount": 210},
                {"merchant_category": "Grocery", "transaction_count": 2, "total_amount": 70, "average_amount": 35},
            ]
        if endpoint == "/anomalies/summary":
            return {"iqr_anomaly_count": 0, "ml_anomaly_count": 2, "overlap_count": 0, "anomaly_percentage": 50}
        if endpoint == "/anomalies/":
            return ROWS[:2]
        if endpoint == "/segments/summary":
            return [
                {"segment_name": "Frequent", "customer_count": 2, "total_spend": 440,
                 "average_transaction_count": 2, "average_anomaly_rate": 0.5},
                {"segment_name": "Occasional", "customer_count": 2, "total_spend": 50,
                 "average_transaction_count": 1, "average_anomaly_rate": 0},
            ]
        if endpoint == "/customers/top":
            return []
        return []

    def download_data(endpoint: str, params: dict | None = None) -> bytes:
        assert endpoint == "/investigations/export"
        params = dict(params or {})
        export_calls.append(params)
        content = pd.DataFrame(filter_rows(params)).to_csv(index=False).encode("utf-8")
        downloaded_csv.append(content)
        return content

    monkeypatch.setattr(api_client, "fetch_data", fetch_data)
    monkeypatch.setattr(api_client, "download_data", download_data)
    return investigation_calls, export_calls, downloaded_csv


def widget(elements, key: str):
    return next(element for element in elements if element.key == key)


def visible_investigation_ids(at) -> set[str]:
    table = at.dataframe[-1].value
    return set(table["transaction_id"].astype(str))


def test_investigation_filter_changes_and_export_follow_active_filters(monkeypatch):
    from streamlit.testing.v1 import AppTest

    calls, exports, downloaded_csv = install_api_mocks(monkeypatch)
    at = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    assert not at.exception
    assert visible_investigation_ids(at) == {"t-1", "t-2", "t-3", "t-4"}
    assert calls[-1]["date_from"] == "2024-01-01" and calls[-1]["date_to"] == "2024-02-28"

    at = widget(at.selectbox, "investigation_status").set_value("flagged").run()
    assert not at.exception and visible_investigation_ids(at) == {"t-1", "t-3"}
    at = widget(at.selectbox, "investigation_status").set_value("normal").run()
    assert not at.exception and visible_investigation_ids(at) == {"t-2", "t-4"}
    at = widget(at.selectbox, "investigation_status").set_value("flagged").run()
    at = widget(at.selectbox, "investigation_category").set_value("Amazon").run()
    assert not at.exception and visible_investigation_ids(at) == {"t-3"}
    at = widget(at.text_input, "investigation_id").set_value("t-3").run()
    at = widget(at.number_input, "investigation_min").set_value(100).run()
    at = widget(at.number_input, "investigation_max").set_value(150).run()
    at = at.date_input[0].set_value((date(2024, 2, 1), date(2024, 2, 28))).run()
    assert not at.exception and visible_investigation_ids(at) == {"t-3"}
    expected = {"anomaly_status": "flagged", "merchant_category": "Amazon", "transaction_id": "t-3",
                "amount_min": 100.0, "amount_max": 150.0, "date_from": "2024-02-01", "date_to": "2024-02-28"}
    assert all(calls[-1].get(key) == value for key, value in expected.items())
    assert all(exports[-1].get(key) == value for key, value in expected.items())
    assert "page" not in exports[-1] and "page_size" not in exports[-1]
    exported = pd.read_csv(pd.io.common.BytesIO(downloaded_csv[-1]))
    assert len(exported) == 1
    assert exported["transaction_id"].tolist() == ["t-3"]
    assert {"amount", "merchant_category", "ml_anomaly", "synthetic_fraud_label"}.issubset(exported.columns)

    button = at.get("download_button")[0]
    assert hasattr(button, "click")
    clicked = button.click().run()
    assert not clicked.exception
    assert clicked.get("download_button")[0].value is True
    assert widget(clicked.selectbox, "investigation_category").value == "Amazon"
    assert widget(clicked.selectbox, "investigation_status").value == "flagged"
    assert widget(clicked.text_input, "investigation_id").value == "t-3"
    assert widget(clicked.number_input, "investigation_min").value == 100.0
    assert widget(clicked.number_input, "investigation_max").value == 150.0
    assert clicked.date_input[0].value == (date(2024, 2, 1), date(2024, 2, 28))


def test_investigation_empty_results_and_invalid_amount_range(monkeypatch):
    from streamlit.testing.v1 import AppTest

    calls, exports, downloaded_csv = install_api_mocks(monkeypatch)
    at = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    previous_call_count = len(calls)
    at = widget(at.text_input, "investigation_id").set_value("no-match").run()
    assert not at.exception and len(calls) == previous_call_count + 1
    assert "No transactions match the investigation filters." in " ".join(element.value for element in at.markdown)
    assert len(exports) == previous_call_count  # no CSV export is requested for an empty result
    assert len(downloaded_csv) == previous_call_count

    previous_call_count = len(calls)
    at = widget(at.number_input, "investigation_min").set_value(200).run()
    assert len(calls) == previous_call_count + 1
    previous_call_count = len(calls)
    at = widget(at.number_input, "investigation_max").set_value(100).run()
    assert not at.exception
    assert len(calls) == previous_call_count  # invalid bounds stop before the investigation request
    assert any("Minimum amount must be less than or equal to maximum amount." in element.value for element in at.warning)


def test_dashboard_kpis_match_filtered_api_response(monkeypatch):
    from streamlit.testing.v1 import AppTest

    install_api_mocks(monkeypatch)
    at = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    assert not at.exception
    values = {metric.label: metric.value for metric in at.metric}
    assert values["Total transaction value"] == "$490.00"
    assert values["Transactions"] == "4"
    assert values["Potential anomalies"] == "2"
    assert values["Anomaly rate"] == "50.00%"
    assert values["Active customers"] == "4"
    assert values["Average transaction"] == "$122.50"


def test_assistant_receives_active_dashboard_filters_and_shows_grounded_evidence(monkeypatch):
    from streamlit.testing.v1 import AppTest

    install_api_mocks(monkeypatch)
    calls = []

    def post_data(endpoint: str, payload: dict):
        calls.append((endpoint, payload))
        return {"answer": "Four transactions were in the supplied result.", "intent": "kpi",
                "source": "FinSight Analytics", "data": {"total_transactions": 4, "filters": payload["filters"]}}

    monkeypatch.setattr(api_client, "post_data", post_data)
    at = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    date_widget = next(element for element in at.date_input if element.label == "Analysis period")
    at = date_widget.set_value((date(2024, 2, 1), date(2024, 2, 28))).run()
    category_widget = next(element for element in at.selectbox if element.label == "Merchant Category")
    at = category_widget.set_value("Amazon").run()
    question_widget = next(element for element in at.text_input if element.label == "Your question")
    at = question_widget.set_value("How many transactions are in scope?").run()
    ask_button = next(element for element in at.button if element.label == "Ask FinSight")
    at = ask_button.click().run()

    assert not at.exception
    assert len(calls) == 1
    endpoint, payload = calls[0]
    assert endpoint == "/ai/query"
    assert payload["question"] == "How many transactions are in scope?"
    assert payload["filters"]["merchant_category"] == "Amazon"
    assert payload["filters"]["date_from"] == "2024-02-01"
    assert payload["filters"]["date_to"] == "2024-02-28"
    assert any("Four transactions were in the supplied result." in item.value for item in at.markdown)
