from collections.abc import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st


COLORS = ["#5b8def", "#55c7d9", "#4bd19b", "#f2b866", "#b28cff", "#e57474"]


def section_heading(title: str, caption: str = "") -> None:
    st.markdown(f"## {title}", unsafe_allow_html=False)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


def render_kpis(kpis: dict) -> None:
    cards = [
        ("Total Transactions", f"{kpis.get('total_transactions', 0):,}", "Across selected period"),
        ("Total Transaction Value", f"${kpis.get('total_transaction_amount', 0):,.0f}", "Filtered transaction value"),
        ("Average Transaction", f"${kpis.get('average_transaction_amount', 0):,.2f}", "Average ticket size"),
        ("Unique Customers", f"{kpis.get('unique_customers', 0):,}", "Customers in selected activity"),
        ("Potential Anomalies", f"{kpis.get('potential_anomalies', 0):,}", "Model-flagged activity"),
    ]
    for column, (label, value, description) in zip(st.columns(5), cards):
        with column:
            st.metric(label, value, help=description)
            st.caption(description)


def chart_layout(fig, height: int = 320):
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Sans", "color": "#b8c6d9", "size": 12},
        title_font={"family": "Space Grotesk", "color": "#e8eef8", "size": 15},
        margin={"l": 12, "r": 12, "t": 42, "b": 12},
        showlegend=False,
        hoverlabel={"bgcolor": "#16243a", "font": {"color": "#e8eef8"}},
    )
    fig.update_xaxes(showgrid=False, linecolor="#22344c", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1d2e45", zeroline=False)
    return fig


def render_chart(fig, key: str, height: int = 320) -> None:
    st.plotly_chart(chart_layout(fig, height), width="stretch", config={"displayModeBar": False}, key=key)


def render_empty(message: str) -> None:
    st.markdown(f'<div class="panel"><span class="section-caption">{message}</span></div>', unsafe_allow_html=True)


def format_table(df: pd.DataFrame, currency_columns: Iterable[str] = ()) -> pd.DataFrame:
    display = df.copy()
    for column in currency_columns:
        if column in display.columns:
            display[column] = display[column].map(lambda value: f"${value:,.2f}" if pd.notna(value) else "-")
    if "anomaly_rate" in display.columns:
        display["anomaly_rate"] = display["anomaly_rate"].map(lambda value: f"{value:.1%}" if pd.notna(value) else "-")
    return display