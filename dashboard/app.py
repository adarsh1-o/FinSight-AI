from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import fetch_data, post_data
from dashboard.components import format_table, render_chart, render_empty, render_kpis, section_heading
from dashboard.styles import apply_styles


SPEND_HOVER = "%{y}<br>Total: $%{x:,.2f}<extra></extra>"


st.set_page_config(page_title="FinSight AI | Financial Intelligence Platform", page_icon="FS", layout="wide", initial_sidebar_state="expanded")
apply_styles()


def option_list(endpoint: str) -> list[str]:
    return fetch_data(endpoint) or []


def render_filters() -> tuple[dict, bool]:
    st.sidebar.markdown('<div class="brand-kicker">FinSight AI</div><h2 style="margin-top:0!important">FILTERS</h2>', unsafe_allow_html=True)
    st.sidebar.caption("Shape the intelligence view with active transaction filters.")
    date_range = fetch_data("/date-range") or {}
    min_date = date.fromisoformat(date_range["min_date"]) if date_range.get("min_date") else date.today()
    max_date = date.fromisoformat(date_range["max_date"]) if date_range.get("max_date") else min_date

    st.sidebar.markdown('<div class="sidebar-label">Date Range</div>', unsafe_allow_html=True)
    selected_dates = st.sidebar.date_input("Analysis period", (min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
    selected_start, selected_end = (selected_dates if isinstance(selected_dates, tuple) and len(selected_dates) == 2 else (min_date, max_date))

    st.sidebar.markdown('<div class="sidebar-label">Transaction Context</div>', unsafe_allow_html=True)
    selected_category = st.sidebar.selectbox("Merchant Category", ["All"] + option_list("/categories"))
    selected_payment = st.sidebar.selectbox("Payment Method", ["All"] + option_list("/payment-methods"))
    selected_location = st.sidebar.selectbox("Location", ["All"] + option_list("/locations"))
    selected_type = st.sidebar.selectbox("Transaction Type", ["All"] + option_list("/transaction-types"))
    selected_status = st.sidebar.selectbox("Status", ["All"] + option_list("/statuses"))

    reset = st.sidebar.button("Reset Filters", width="stretch")
    params = {"date_from": selected_start.isoformat(), "date_to": selected_end.isoformat()}
    for key, value in {"merchant_category": selected_category, "payment_method": selected_payment, "location": selected_location, "transaction_type": selected_type, "status": selected_status}.items():
        if value != "All":
            params[key] = value
    st.sidebar.markdown('<div class="sidebar-label">View Status</div>', unsafe_allow_html=True)
    st.sidebar.caption("Showing filtered transaction activity")
    return params, reset


def render_header(api_online: bool) -> None:
    status_class = "" if api_online else "status-offline"
    status_label = "Analytics Engine Online" if api_online else "Analytics Engine Unavailable"
    st.markdown('<div class="brand-kicker">FINANCIAL INTELLIGENCE PLATFORM</div>', unsafe_allow_html=True)
    st.title("FinSight AI")
    st.markdown('<div class="brand-subtitle">Financial analytics, anomaly intelligence and customer behavior</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status {status_class}"><span class="status-dot"></span>{status_label}</div>', unsafe_allow_html=True)


def render_overview(kpis: dict, trends: list) -> None:
    section_heading("Executive Overview", "A focused view of transaction scale and value across the selected period.")
    render_kpis(kpis)
    if not trends:
        render_empty("No trend data is available for the selected filters.")
        return
    df = pd.DataFrame(trends)
    first, second = st.columns(2)
    with first:
        fig = px.bar(df, x="month", y="transaction_count", labels={"month": "Month", "transaction_count": "Transactions"}, title="Monthly transaction volume", color_discrete_sequence=["#5b8def"])
        fig.update_traces(hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>")
        render_chart(fig, "monthly-volume")
    with second:
        fig = px.area(df, x="month", y="transaction_amount", labels={"month": "Month", "transaction_amount": "Value"}, title="Monthly transaction value", color_discrete_sequence=["#55c7d9"])
        fig.update_traces(hovertemplate="%{x}<br>Value: $%{y:,.2f}<extra></extra>")
        render_chart(fig, "monthly-value")


def render_transactions(transactions: list) -> None:
    section_heading("Transaction Intelligence", "Compare activity mix across type, merchant, payment method and status.")
    if not transactions:
        render_empty("No transactions match the current filters.")
        return
    df = pd.DataFrame(transactions)
    dimensions = [("transaction_type", "Transaction type"), ("merchant_category", "Merchant category"), ("payment_method", "Payment method"), ("status", "Status")]
    for column, (field, title) in zip(st.columns(4), dimensions):
        with column:
            counts = df[field].value_counts().rename_axis(field).reset_index(name="count") if field in df else pd.DataFrame()
            if counts.empty:
                render_empty(f"No {title.lower()} data")
            else:
                fig = px.bar(counts, x="count", y=field, orientation="h", title=title, color_discrete_sequence=["#5b8def"])
                fig.update_traces(hovertemplate="%{y}<br>Count: %{x:,}<extra></extra>")
                render_chart(fig, f"{field}-counts", 270)
    section_heading("Spending Analysis", "Where selected-period value is concentrated.")
    by_category = df.groupby("merchant_category", as_index=False).agg(total_spend=("amount", "sum"), average_transaction=("amount", "mean")).sort_values("total_spend", ascending=False).head(10)
    by_type = df.groupby("transaction_type", as_index=False).agg(total_spend=("amount", "sum")).sort_values("total_spend", ascending=False)
    first, second = st.columns(2)
    with first:
        fig = px.bar(by_category, x="total_spend", y="merchant_category", orientation="h", title="Spending by merchant category", color_discrete_sequence=["#4bd19b"])
        fig.update_traces(hovertemplate=SPEND_HOVER)
        render_chart(fig, "spend-category")
    with second:
        fig = px.bar(by_type, x="total_spend", y="transaction_type", orientation="h", title="Spending by transaction type", color_discrete_sequence=["#f2b866"])
        fig.update_traces(hovertemplate="%{y}<br>Total: $%{x:,.2f}<extra></extra>")
        render_chart(fig, "spend-type")


def render_anomalies(params: dict) -> None:
    section_heading("Anomaly Intelligence", "Potential statistical anomalies and model-flagged activity, not confirmed fraud.")
    summary = fetch_data("/anomalies/summary", params=params) or {}
    cards = [("IQR Outliers", summary.get("iqr_anomaly_count", 0)), ("ML Anomalies", summary.get("ml_anomaly_count", 0)), ("Overlap", summary.get("overlap_count", 0)), ("Anomaly Rate", f"{summary.get('anomaly_percentage', 0):.2f}%")]
    for column, (label, value) in zip(st.columns(4), cards):
        with column:
            st.metric(label, value, help="Potential statistical anomaly")
    anomalies = fetch_data("/anomalies/", params={**params, "limit": 15}) or []
    if anomalies:
        df = pd.DataFrame(anomalies)
        columns = ["transaction_id", "transaction_date", "amount", "transaction_type", "merchant_category", "payment_method", "location", "iqr_anomaly", "ml_anomaly"]
        display = format_table(df[[column for column in columns if column in df]], ["amount"])
        st.dataframe(display, width="stretch", hide_index=True)
    else:
        render_empty("No potential anomalies match the current filters.")


def render_customers(params: dict) -> None:
    section_heading("Customer Intelligence", "Stage 4 segment assignments with metrics recalculated for the selected activity.")
    segments = fetch_data("/segments/summary", params=params) or []
    if segments:
        df = pd.DataFrame(segments)
        first, second = st.columns(2)
        with first:
            fig = px.bar(df, x="customer_count", y="segment_name", orientation="h", title="Customer segment distribution", color_discrete_sequence=["#5b8def"])
            render_chart(fig, "segment-distribution")
        with second:
            fig = px.bar(df, x="total_spend", y="segment_name", orientation="h", title="Total spend by segment", color_discrete_sequence=["#4bd19b"])
            fig.update_traces(hovertemplate=SPEND_HOVER)
            render_chart(fig, "segment-spend")
        first, second = st.columns(2)
        with first:
            fig = px.bar(df, x="average_transaction_count", y="segment_name", orientation="h", title="Transaction frequency by segment", color_discrete_sequence=["#55c7d9"])
            render_chart(fig, "segment-frequency")
        with second:
            fig = px.bar(df, x="average_anomaly_rate", y="segment_name", orientation="h", title="Anomaly rate by segment", color_discrete_sequence=["#f2b866"])
            fig.update_xaxes(tickformat=".1%")
            render_chart(fig, "segment-anomaly")
    else:
        render_empty("No customer segment data matches the current filters.")
    top_customers = fetch_data("/customers/top", params={**params, "limit": 10}) or []
    if top_customers:
        display = format_table(pd.DataFrame(top_customers), ["total_spend"])
        ordered = [column for column in ["customer_id", "segment_name", "total_spend", "transaction_count", "anomaly_rate"] if column in display]
        st.dataframe(display[ordered], width="stretch", hide_index=True)


def render_assistant() -> None:
    section_heading("AI Financial Assistant", "Ask grounded questions about the currently selected FinSight activity.")
    examples = [
        "What is the total transaction value?",
        "Which merchant category has the highest spending?",
        "How many potential anomalies were detected?",
        "Which customer segment has the highest spending?",
        "Explain the major spending trends.",
    ]
    if "ai_history" not in st.session_state:
        st.session_state.ai_history = []
    st.markdown('<div class="assistant"><div class="eyebrow">Grounded analytics</div><div class="assistant-title">Ask FinSight about your financial data</div><div class="assistant-copy">Answers are based on verified FinSight analytics and the active dashboard filters.</div></div>', unsafe_allow_html=True)
    selected_example = st.selectbox("Example questions", ["Choose an example..."] + examples, label_visibility="collapsed")
    question = st.text_input("Your question", value="" if selected_example == "Choose an example..." else selected_example, placeholder="e.g. Which category has the highest spending?", label_visibility="collapsed")
    if st.button("Ask FinSight", type="primary", width="stretch"):
        if not question.strip():
            st.warning("Enter a question about the FinSight data.")
        else:
            with st.spinner("Retrieving verified FinSight data and preparing an answer..."):
                result = post_data("/ai/query", {"question": question, "filters": params})
            if result:
                st.session_state.ai_history.append({"question": question, "result": result})
    for item in reversed(st.session_state.ai_history):
        result = item["result"]
        with st.container(border=True):
            st.caption(f"You asked: {item['question']}")
            st.markdown(result.get("answer", "The AI service returned no answer."))
            st.caption(f"Source: {result.get('source', 'FinSight Analytics')} · Intent: {result.get('intent', 'unknown')}")


params, reset = render_filters()
if reset:
    st.cache_data.clear()
    st.rerun()
health = fetch_data("/date-range")
render_header(health is not None)
kpis = fetch_data("/kpis/", params=params) or {}
trends = fetch_data("/trends/monthly", params=params) or []
transactions = fetch_data("/transactions", params={**params, "limit": 1000}) or []
overview_tab, transaction_tab, anomaly_tab, customer_tab, assistant_tab = st.tabs(["Overview", "Transactions", "Anomalies", "Customers", "AI Assistant"])
with overview_tab:
    render_overview(kpis, trends)
with transaction_tab:
    render_transactions(transactions)
with anomaly_tab:
    render_anomalies(params)
with customer_tab:
    render_customers(params)
with assistant_tab:
    render_assistant()
st.markdown('<div class="footer">FinSight AI · Financial Analytics Platform<br><span>Data → Analytics → ML → API → AI</span></div>', unsafe_allow_html=True)
