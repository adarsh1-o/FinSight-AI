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
        ("Total transaction value", f"${(kpis.get('total_transaction_amount') or 0):,.2f}", "Value across the selected activity", ":material/payments:"),
        ("Transactions analyzed", f"{(kpis.get('total_transactions') or 0):,}", "Count in the selected period", ":material/receipt_long:"),
        ("Potential anomalies", f"{(kpis.get('potential_anomalies') or 0):,}", "Model-flagged activity; not confirmed fraud", ":material/warning:"),
        ("Anomaly rate", f"{(kpis.get('anomaly_percentage') or 0):.2f}%", "Share of transactions flagged by the model", ":material/monitoring:"),
        ("Active customers", f"{(kpis.get('unique_customers') or 0):,}", "Unique customers with activity in this period", ":material/groups:"),
    ]
    with st.container(key="kpi-strip", horizontal=True, gap="small", border=True):
        for label, value, description, icon in cards:
            st.metric(label, value, help=description, icon=icon)


def chart_layout(fig, height: int = 320):
    has_legend = len(fig.data) > 1 and any(getattr(trace, "name", "") for trace in fig.data)
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "sans-serif", "color": "#92A8BE", "size": 11},
        title_font={"family": "sans-serif", "color": "#F1F5F9", "size": 14},
        margin={"l": 12, "r": 12, "t": 38, "b": 12},
        showlegend=has_legend,
        legend={"orientation": "h", "y": 1.12, "x": 0, "font": {"size": 10}},
        hoverlabel={"bgcolor": "#16243a", "font": {"color": "#e8eef8"}},
    )
    fig.update_xaxes(showgrid=False, linecolor="#203C56", zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(32,60,86,.55)", linecolor="#203C56", zeroline=False, automargin=True)
    return fig


def render_chart(fig, key: str, height: int = 320) -> None:
    st.plotly_chart(chart_layout(fig, height), width="stretch", config={"displayModeBar": False, "responsive": True}, key=key)


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
