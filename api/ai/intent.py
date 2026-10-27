from enum import Enum


class Intent(str, Enum):
    KPI = "kpi"
    TREND = "trend"
    MERCHANT_CATEGORY = "merchant_category"
    TRANSACTION_TYPE = "transaction_type"
    PAYMENT_METHOD = "payment_method"
    STATUS = "status"
    LOCATION = "location"
    ANOMALY = "anomaly"
    CUSTOMER = "customer"
    SEGMENT = "segment"
    DEFINITION = "definition"
    DOCUMENTATION = "documentation"
    UNSUPPORTED = "unsupported"


def detect_intent(question: str) -> Intent:
    normalized = question.casefold()
    if not normalized.strip():
        return Intent.UNSUPPORTED
    documentation_question = any(phrase in normalized for phrase in (
        "data dictionary", "project documentation", "methodology", "what does",
        "what is the definition", "define ", "explain the metric", "calculated",
        "calculation", "what is an iqr", "explain iqr", "what is isolation forest",
        "explain isolation forest", "what is an anomaly", "explain anomaly",
        "contamination", "which columns", "what columns", "which fields",
        "api endpoint", "what does the endpoint", "how does the endpoint",
    )) or (
        "algorithm" in normalized and any(word in normalized for word in ("anomal", "segment", "cluster"))
    ) or (
        "feature" in normalized and any(word in normalized for word in ("anomal", "segment", "cluster"))
    ) or (
        any(word in normalized for word in ("identified", "computed", "derived"))
        and any(word in normalized for word in ("how", "method", "methodology"))
    )
    if documentation_question:
        return Intent.DOCUMENTATION
    if any(word in normalized for word in ("iqr", "isolation forest", "what is an anomaly", "potential anomaly")) and any(word in normalized for word in ("what is", "explain", "mean", "definition")):
        return Intent.DEFINITION
    if any(word in normalized for word in ("anomal", "outlier", "fraud")):
        return Intent.ANOMALY
    if any(word in normalized for word in ("segment", "cluster")):
        return Intent.SEGMENT
    if any(word in normalized for word in ("customer", "client")):
        return Intent.CUSTOMER
    if any(word in normalized for word in ("trend", "monthly", "month over month", "over time")):
        return Intent.TREND
    if any(word in normalized for word in ("merchant", "category", "spending by category")):
        return Intent.MERCHANT_CATEGORY
    if any(word in normalized for word in ("payment", "card", "wire", "cash")):
        return Intent.PAYMENT_METHOD
    if any(word in normalized for word in ("transaction type", "purchase", "transfer", "withdrawal")):
        return Intent.TRANSACTION_TYPE
    if any(word in normalized for word in ("status", "completed", "pending", "failed")):
        return Intent.STATUS
    if any(word in normalized for word in ("location", "local", "foreign")):
        return Intent.LOCATION
    if any(word in normalized for word in ("total", "average", "value", "amount", "count", "how many", "kpi", "metric")):
        return Intent.KPI
    return Intent.UNSUPPORTED
