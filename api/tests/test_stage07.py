import json
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from api.main import app
from api.pipeline.evaluation import evaluate_anomalies
from api.pipeline.transactions import run_pipeline
from api.pipeline.validation import DatasetValidationError, validate_transactions
from api.routers.investigations import anomaly_evaluation, export_investigations, investigations, quality_summary

client = TestClient(app)


def sample_transactions(rows=12):
    return pd.DataFrame({
        "transaction_id": [f"t-{i:03}" for i in range(rows)],
        "customer_id": [f"c-{i % 4}" for i in range(rows)],
        "account_id": [f"a-{i % 4}" for i in range(rows)],
        "transaction_date": pd.date_range("2024-01-01", periods=rows, freq="h").astype(str),
        "amount": [float(i + 1) for i in range(rows)],
        "transaction_type": ["Purchase"] * rows,
        "merchant_category": ["Grocery"] * rows,
        "payment_method": ["Card"] * rows,
        "location": ["Local"] * rows,
        "status": ["Completed"] * rows,
    })


def test_validation_accepts_valid_rows_and_warns_on_unusual_categories():
    frame = sample_transactions()
    frame.loc[0, "merchant_category"] = "NewCategory"
    result = validate_transactions(frame)
    assert result["row_count"] == 12
    assert any("Unexpected merchant_category" in message for message in result["warnings"])


@pytest.mark.parametrize("change, message", [
    (lambda d: d.drop(columns="transaction_id"), "Missing required transaction columns"),
    (lambda d: d.assign(amount="bad"), "amount contains"),
    (lambda d: d.assign(transaction_date=d["transaction_date"].where(d.index != d.index[-1], "2024-02-31 10:00:00")), "invalid timestamp"),
    (lambda d: d.assign(transaction_id=""), "blank identifiers"),
])
def test_validation_rejects_critical_data_errors(change, message):
    with pytest.raises(DatasetValidationError, match=message):
        validate_transactions(change(sample_transactions()))


def test_validation_reports_missing_values_and_duplicate_ids():
    frame = sample_transactions()
    frame.loc[0, "merchant_category"] = None
    frame.loc[1, "transaction_id"] = frame.loc[0, "transaction_id"]
    result = validate_transactions(frame)
    assert result["duplicate_transaction_ids"] == 2
    assert result["missing_values"]["merchant_category"] == 1


def test_evaluation_maps_isolation_forest_predictions_correctly():
    result = evaluate_anomalies(pd.DataFrame({"is_fraud": [1, 1, 0, 0], "isolation_prediction": [-1, 1, -1, 1]}))
    assert result["confusion_matrix"] == {"true_negative": 1, "false_positive": 1, "false_negative": 1, "true_positive": 1}
    assert result["precision"] == .5
    assert result["recall"] == .5
    assert result["f1_score"] == .5
    assert result["false_positive_rate"] == .5


def test_evaluation_handles_missing_labels_empty_and_no_positive_predictions():
    assert evaluate_anomalies(pd.DataFrame())["status"] == "unavailable"
    assert evaluate_anomalies(pd.DataFrame({"isolation_prediction": [1]}))["status"] == "unavailable"
    no_flags = evaluate_anomalies(pd.DataFrame({"is_fraud": [0, 1], "isolation_prediction": [1, 1]}))
    assert no_flags["precision"] == no_flags["recall"] == no_flags["f1_score"] == 0


def test_evaluation_rejects_nonbinary_labels_and_invalid_prediction_codes():
    bad_labels = evaluate_anomalies(pd.DataFrame({"is_fraud": [0, 2], "isolation_prediction": [1, -1]}))
    bad_predictions = evaluate_anomalies(pd.DataFrame({"is_fraud": [0, 1], "isolation_prediction": [0, -1]}))
    assert bad_labels["status"] == bad_predictions["status"] == "unavailable"


def test_pipeline_is_repeatable_and_replaces_output_safely(tmp_path):
    source = tmp_path / "transactions.csv"
    output = tmp_path / "processed.csv"
    report = tmp_path / "summary.json"
    frame = sample_transactions()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    frame.to_csv(source, index=False)
    first = run_pipeline(source, output, report)
    first_output = pd.read_csv(output)
    second = run_pipeline(source, output, report)
    second_output = pd.read_csv(output)
    assert first["input_rows"] == 13 and first["output_rows"] == 12
    assert first["rows_removed"] == first["duplicate_rows"] == 1
    assert first["anomalies_flagged"] == second["anomalies_flagged"]
    pd.testing.assert_frame_equal(first_output, second_output)
    assert json.loads(report.read_text())["status"] == "success"
    assert json.loads(report.read_text())["report_path"] == str(report)


def test_pipeline_reports_missing_file_and_conflicting_ids(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_pipeline(tmp_path / "missing.csv", tmp_path / "out.csv")
    source = tmp_path / "conflict.csv"
    frame = sample_transactions()
    frame.loc[1, "transaction_id"] = frame.loc[0, "transaction_id"]
    frame.to_csv(source, index=False)
    with pytest.raises(DatasetValidationError, match="still have duplicate transaction IDs"):
        run_pipeline(source, tmp_path / "out.csv")


def test_stage07_api_summaries_and_investigation_filters():
    quality = client.get("/api/quality/summary")
    assert quality.status_code == 200
    assert quality.json()["row_count"] == 100050
    evaluation = client.get("/api/anomalies/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["status"] == "synthetic_benchmark"
    result = client.get("/api/investigations", params={"anomaly_status": "flagged", "page_size": 3})
    assert result.status_code == 200
    assert len(result.json()["items"]) == 3
    assert result.json()["items"][0]["ml_anomaly"] == 1
    assert "synthetic_fraud_label" in result.json()["items"][0]
    assert "probability" in result.json()["score_note"] or "not a fraud probability" in result.json()["score_note"]


def test_investigation_api_rejects_invalid_filters_and_exports_csv():
    assert client.get("/api/investigations", params={"amount_min": 20, "amount_max": 10}).status_code == 422
    assert client.get("/api/investigations", params={"anomaly_status": "fraud"}).status_code == 422
    exported = client.get("/api/investigations/export", params={"anomaly_status": "flagged"})
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "transaction_id" in exported.text.splitlines()[0]


def test_stage07_route_functions_filter_search_and_export_matching_rows():
    quality = quality_summary()
    evaluation = anomaly_evaluation()
    assert quality["status"] == "needs_cleaning"
    assert quality["duplicate_transaction_ids"] == 100
    assert evaluation["status"] == "synthetic_benchmark"
    common = {"date_from": None, "date_to": None, "transaction_type": None, "merchant_category": None,
              "payment_method": None, "status": None, "location": None, "customer_id": None}
    page = investigations(page=1, page_size=3, anomaly_status="flagged", transaction_id=None,
                          amount_min=None, amount_max=None, sort_by="score", order="asc", **common)
    assert page["total"] == 5000
    selected = page["items"][0]
    searched = investigations(page=1, page_size=10, anomaly_status="all", transaction_id=selected["transaction_id"],
                              amount_min=None, amount_max=None, sort_by="score", order="asc", **common)
    assert searched["total"] == 1
    response = export_investigations(anomaly_status="flagged", transaction_id=selected["transaction_id"],
                                     amount_min=None, amount_max=None, sort_by="score", order="asc", **common)
    exported = pd.read_csv(io.StringIO(response.body.decode("utf-8")))
    assert len(exported) == 1
    assert exported.iloc[0].transaction_id == selected["transaction_id"]
    assert bool(exported.iloc[0].synthetic_fraud_label) == bool(selected["synthetic_fraud_label"])
    with pytest.raises(HTTPException, match="amount_min") as error:
        investigations(page=1, page_size=3, anomaly_status="all", transaction_id=None, amount_min=20,
                       amount_max=10, sort_by="score", order="asc", **common)
    assert error.value.status_code == 422
    assert "/api/investigations" in app.openapi()["paths"]
