from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import download_data, fetch_data, post_data
from dashboard.components import format_table, render_chart, render_empty, render_kpis, section_heading
from dashboard.styles import apply_styles


SPEND_HOVER = "%{y}<br>Total: $%{x:,.2f}<extra></extra>"


st.set_page_config(page_title="FinSight AI | Financial Intelligence Platform", page_icon=":material/account_balance:", layout="wide", initial_sidebar_state="expanded")
apply_styles()


def option_list(endpoint: str) -> list[str]:
    return fetch_data(endpoint) or []


def render_filters() -> tuple[dict, bool]:
    st.sidebar.caption("FINSIGHT AI · FINANCIAL INTELLIGENCE")
    st.sidebar.subheader("Filters", icon=":material/filter_list:")
    st.sidebar.caption("Refine analytics and assistant context by transaction activity.")
    date_range = fetch_data("/date-range") or {}
    min_date = date.fromisoformat(date_range["min_date"]) if date_range.get("min_date") else date.today()
    max_date = date.fromisoformat(date_range["max_date"]) if date_range.get("max_date") else min_date

    st.sidebar.markdown("**Analysis period**")
    selected_dates = st.sidebar.date_input("Analysis period", (min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
    selected_start, selected_end = (selected_dates if isinstance(selected_dates, tuple) and len(selected_dates) == 2 else (min_date, max_date))

    st.sidebar.markdown("**Transaction context**")
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
    st.sidebar.caption("Filters apply to analytics and AI answers.")
    return params, reset


def render_header(api_online: bool) -> None:
    title, status = st.columns([5, 1], vertical_alignment="center")
    with title:
        st.caption("FINANCIAL INTELLIGENCE PLATFORM")
        st.title("FinSight AI", icon=":material/account_balance:")
        st.markdown('<div class="brand-subtitle">Transaction analytics, anomaly review and customer intelligence</div>', unsafe_allow_html=True)
    with status:
        if api_online:
            st.badge("Analytics API available", icon=":material/check_circle:", color="green")
        else:
            st.badge("Analytics API unavailable", icon=":material/error:", color="red")


def render_overview(kpis: dict, trends: list, categories: list, segments: list) -> None:
    section_heading("Executive Overview", "A focused view of transaction scale and value across the selected period.")
    render_kpis(kpis)
    if not trends:
        render_empty("No trend data is available for the selected filters.")
    else:
        df = pd.DataFrame(trends)
        first, second = st.columns(2)
        with first:
            fig = px.bar(df, x="month", y="transaction_count", labels={"month": "Month", "transaction_count": "Transactions"}, title="Monthly transaction volume", color_discrete_sequence=["#5b8def"])
            fig.update_traces(hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>")
            fig.update_yaxes(tickformat=",")
            render_chart(fig, "monthly-volume")
        with second:
            fig = px.area(df, x="month", y="transaction_amount", labels={"month": "Month", "transaction_amount": "Transaction value ($)"}, title="Monthly transaction value", color_discrete_sequence=["#55c7d9"])
            fig.update_traces(hovertemplate="%{x}<br>Value: $%{y:,.2f}<extra></extra>")
            fig.update_yaxes(tickprefix="$", tickformat="~s")
            render_chart(fig, "monthly-value")

        if "potential_anomalies" in df:
            fig = px.bar(df, x="month", y="potential_anomalies", labels={"month": "Month", "potential_anomalies": "Potential anomalies"}, title="Monthly model-flagged activity", color_discrete_sequence=["#f2b866"])
            fig.update_traces(hovertemplate="%{x}<br>Potential anomalies: %{y:,}<extra></extra>")
            fig.update_yaxes(tickformat=",")
            render_chart(fig, "monthly-anomaly-activity")
        else:
            render_empty("Monthly potential anomaly counts are not available.")

    category_col, segment_col = st.columns(2)
    with category_col:
        if categories:
            category_df = pd.DataFrame(categories).head(8).sort_values("total_amount", ascending=True)
            fig = px.bar(category_df, x="total_amount", y="merchant_category", orientation="h", labels={"total_amount": "Transaction value ($)", "merchant_category": "Merchant category"}, title="Category spend", color_discrete_sequence=["#4bd19b"])
            fig.update_traces(hovertemplate="%{y}<br>Transaction value: $%{x:,.2f}<extra></extra>")
            fig.update_xaxes(tickprefix="$", tickformat="~s")
            render_chart(fig, "overview-category-spend", 360)
        else:
            render_empty("No category activity matches the selected filters.")
    with segment_col:
        if segments:
            segment_df = pd.DataFrame(segments).sort_values("customer_count", ascending=True)
            fig = px.bar(segment_df, x="customer_count", y="segment_name", orientation="h", labels={"customer_count": "Customers", "segment_name": "Customer segment"}, title="Customer segment distribution", color_discrete_sequence=["#55c7d9"])
            fig.update_traces(hovertemplate="%{y}<br>Customers: %{x:,}<extra></extra>")
            fig.update_xaxes(tickformat=",")
            render_chart(fig, "overview-segment-distribution", 360)
        else:
            render_empty("No customer segment data matches the selected filters.")


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
                fig = px.bar(counts, x="count", y=field, orientation="h", labels={"count": "Transactions", field: title}, title=title, color_discrete_sequence=["#5b8def"])
                fig.update_traces(hovertemplate="%{y}<br>Count: %{x:,}<extra></extra>")
                render_chart(fig, f"{field}-counts", 270)
    section_heading("Spending Analysis", "Where selected-period value is concentrated.")
    by_category = df.groupby("merchant_category", as_index=False).agg(total_spend=("amount", "sum"), average_transaction=("amount", "mean")).sort_values("total_spend", ascending=False).head(10)
    by_type = df.groupby("transaction_type", as_index=False).agg(total_spend=("amount", "sum")).sort_values("total_spend", ascending=False)
    first, second = st.columns(2)
    with first:
        fig = px.bar(by_category, x="total_spend", y="merchant_category", orientation="h", labels={"total_spend": "Transaction value ($)", "merchant_category": "Merchant category"}, title="Spending by merchant category", color_discrete_sequence=["#4bd19b"])
        fig.update_traces(hovertemplate=SPEND_HOVER)
        fig.update_xaxes(tickprefix="$", tickformat="~s")
        render_chart(fig, "spend-category")
    with second:
        fig = px.bar(by_type, x="total_spend", y="transaction_type", orientation="h", labels={"total_spend": "Transaction value ($)", "transaction_type": "Transaction type"}, title="Spending by transaction type", color_discrete_sequence=["#f2b866"])
        fig.update_traces(hovertemplate="%{y}<br>Total: $%{x:,.2f}<extra></extra>")
        fig.update_xaxes(tickprefix="$", tickformat="~s")
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


def render_customers(params: dict, segments: list | None = None) -> None:
    section_heading("Customer Intelligence", "Stage 4 segment assignments with metrics recalculated for the selected activity.")
    segments = segments if segments is not None else (fetch_data("/segments/summary", params=params) or [])
    if segments:
        df = pd.DataFrame(segments)
        first, second = st.columns(2)
        with first:
            fig = px.bar(df, x="customer_count", y="segment_name", orientation="h", labels={"customer_count": "Customers", "segment_name": "Segment"}, title="Customer segment distribution", color_discrete_sequence=["#5b8def"])
            fig.update_traces(hovertemplate="%{y}<br>Customers: %{x:,}<extra></extra>")
            render_chart(fig, "segment-distribution")
        with second:
            fig = px.bar(df, x="total_spend", y="segment_name", orientation="h", labels={"total_spend": "Transaction value ($)", "segment_name": "Segment"}, title="Total spend by segment", color_discrete_sequence=["#4bd19b"])
            fig.update_traces(hovertemplate=SPEND_HOVER)
            fig.update_xaxes(tickprefix="$", tickformat="~s")
            render_chart(fig, "segment-spend")
        first, second = st.columns(2)
        with first:
            fig = px.bar(df, x="average_transaction_count", y="segment_name", orientation="h", labels={"average_transaction_count": "Average transactions per customer", "segment_name": "Segment"}, title="Transaction frequency by segment", color_discrete_sequence=["#55c7d9"])
            fig.update_traces(hovertemplate="%{y}<br>Average transactions: %{x:.2f}<extra></extra>")
            render_chart(fig, "segment-frequency")
        with second:
            fig = px.bar(df, x="average_anomaly_rate", y="segment_name", orientation="h", labels={"average_anomaly_rate": "Potential anomaly rate", "segment_name": "Segment"}, title="Potential anomaly rate by segment", color_discrete_sequence=["#f2b866"])
            fig.update_traces(hovertemplate="%{y}<br>Potential anomaly rate: %{x:.1%}<extra></extra>")
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
    section_heading("AI financial assistant", "Ask grounded questions about FinSight analytics and project methodology.")
    examples = [
        "What is the total transaction value?",
        "Which merchant category has the highest spending?",
        "How many potential anomalies were detected?",
        "Which customer segment has the highest spending?",
        "Explain the major spending trends.",
    ]
    if "ai_history" not in st.session_state:
        st.session_state.ai_history = []
    st.markdown('<div class="assistant"><div class="eyebrow">Grounded analytics</div><div class="assistant-title">Your financial activity, with evidence</div><div class="assistant-copy">Answers use verified FinSight analytics, retrieved project documentation and the active filters.</div></div>', unsafe_allow_html=True)
    selected_example = st.selectbox("Example questions", ["Choose an example..."] + examples, label_visibility="collapsed")
    question = st.text_input("Your question", value="" if selected_example == "Choose an example..." else selected_example, placeholder="e.g. Which category has the highest spending?", label_visibility="collapsed")
    if st.button("Ask FinSight", type="primary", width="stretch", icon=":material/send:"):
        if not question.strip():
            st.warning("Enter a question about the FinSight data.")
        else:
            with st.spinner("Retrieving verified FinSight data and preparing an answer..."):
                result = post_data("/ai/query", {"question": question, "filters": params})
            if result:
                st.session_state.ai_history.append({"question": question, "result": result})
    for item in reversed(st.session_state.ai_history):
        result = item["result"]
        with st.chat_message("user"):
            st.markdown(item["question"])
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            st.markdown(result.get("answer", "The AI service returned no answer."))
            st.caption(f"Source: {result.get('source', 'FinSight Analytics')} · Intent: {result.get('intent', 'unknown')}")
            data = result.get("data") or {}
            evidence = {key: value for key, value in data.items() if key not in {"filters", "documentation"}}
            if evidence:
                with st.expander("View verified analytics evidence", icon=":material/fact_check:"):
                    st.json(evidence, expanded=False)
            documents = data.get("documentation") or []
            if documents:
                with st.expander(f"Retrieved documentation · {len(documents)} source(s)", icon=":material/menu_book:"):
                    for document in documents:
                        source = document.get("source", "Project documentation")
                        section = document.get("section", "")
                        st.markdown(f"**{source}**" + (f" · {section}" if section else ""))
                        st.caption(document.get("excerpt", ""))


def render_investigations(params: dict) -> None:
    section_heading("Transaction Investigation", "Review flagged transactions alongside their original context.")
    st.caption("Isolation Forest scores rank unusual records; they are not calibrated fraud probabilities. Synthetic labels are generated benchmark labels, not verified case outcomes.")
    first, second, third, fourth = st.columns(4)
    with first:
        anomaly = st.selectbox("Model status", ["all", "flagged", "normal"], format_func=lambda value: {"all": "All transactions", "flagged": "Potential anomaly", "normal": "Model normal"}[value], key="investigation_status")
    with second:
        transaction_id = st.text_input("Search transaction ID", key="investigation_id").strip()
    with third:
        amount_min = st.number_input("Minimum amount", min_value=0.0, value=0.0, key="investigation_min")
    with fourth:
        amount_max = st.number_input("Maximum amount (0 = no limit)", min_value=0.0, value=0.0, key="investigation_max")
    category = st.selectbox("Investigation category", ["All"] + option_list("/categories"), key="investigation_category")
    if amount_min > amount_max > 0:
        st.warning("Minimum amount must be less than or equal to maximum amount.")
        return
    query = {**params, "anomaly_status": anomaly, "page": 1, "page_size": 500, "sort_by": "score", "order": "asc"}
    if category != "All":
        query["merchant_category"] = category
    if transaction_id:
        query["transaction_id"] = transaction_id
    if amount_min > 0:
        query["amount_min"] = amount_min
    if amount_max > 0:
        query["amount_max"] = amount_max
    result = fetch_data("/investigations", params=query) or {}
    items = result.get("items", [])
    st.caption(f"{result.get('total', 0):,} matching transactions · sorted by lowest anomaly score")
    if not items:
        render_empty("No transactions match the investigation filters.")
        return
    df = pd.DataFrame(items)
    columns = ["transaction_id", "transaction_date", "customer_id", "amount", "transaction_type", "merchant_category", "payment_method", "status", "isolation_prediction", "isolation_score", "ml_anomaly", "synthetic_fraud_label"]
    display = df[[column for column in columns if column in df]].copy()
    if "isolation_prediction" in display:
        display["review_status"] = display["isolation_prediction"].map({-1: "Potential anomaly", 1: "Model normal"})
        display.drop(columns=["isolation_prediction"], inplace=True)
    if "synthetic_fraud_label" in display:
        display["synthetic_fraud_label"] = display["synthetic_fraud_label"].map({True: "Synthetic positive", False: "Synthetic negative"})
    display = format_table(display, ["amount"])
    def highlight_flagged(row):
        color = "background-color: #fff0dc" if row.get("ml_anomaly") == 1 else ""
        return [color] * len(row)
    st.dataframe(display.style.apply(highlight_flagged, axis=1), width="stretch", hide_index=True, height=450)
    st.caption("The isolation score ranks unusual records; it is not a calibrated fraud probability. Synthetic labels are benchmark labels only.")
    export_query = {key: value for key, value in query.items() if key not in {"page", "page_size"}}
    csv_bytes = download_data("/investigations/export", params=export_query)
    if csv_bytes:
        st.download_button("Download filtered results as CSV", csv_bytes, "finsight_investigations.csv", "text/csv", icon=":material/download:")


params, reset = render_filters()
if reset:
    st.cache_data.clear()
    st.rerun()
health = fetch_data("/date-range")
render_header(health is not None)
kpis = fetch_data("/kpis/", params=params) or {}
trends = fetch_data("/trends/monthly", params=params) or []
category_summary = fetch_data("/transactions/summary/categories", params=params) or []
segments = fetch_data("/segments/summary", params=params) or []
transactions = fetch_data("/transactions", params={**params, "limit": 1000}) or []
overview_tab, transaction_tab, anomaly_tab, investigation_tab, customer_tab, assistant_tab = st.tabs([
    ":material/dashboard: Overview",
    ":material/receipt_long: Transactions",
    ":material/query_stats: Anomalies",
    ":material/search: Investigate",
    ":material/groups: Customers",
    ":material/auto_awesome: AI assistant",
])
with overview_tab:
    render_overview(kpis, trends, category_summary, segments)
with transaction_tab:
    render_transactions(transactions)
with anomaly_tab:
    render_anomalies(params)
with investigation_tab:
    render_investigations(params)
with customer_tab:
    render_customers(params, segments)
with assistant_tab:
    render_assistant()
st.caption("FinSight AI · Data → Analytics → ML → API → grounded AI")
