import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#f1f5f9; --muted:#92a8be; --navy:#07111f; --panel:#0d1b2b; --panel-raised:#12253a; --line:#203c56; --blue:#4f8fff; --cyan:#35d6e7; --green:#29d3a2; --amber:#f5b942; --coral:#ff5874; }
        .stApp { background:var(--navy); color:var(--ink); }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stAppViewContainer"] > .main .block-container { max-width:1880px; padding:1.05rem 1.6rem 2.2rem; }
        [data-testid="stSidebar"] { background:#091726; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding:1.05rem .9rem; }
        h1,h2,h3 { letter-spacing:-.025em !important; color:var(--ink) !important; }
        h1 { font-size:1.55rem !important; margin:0 !important; }
        h2 { font-size:1.2rem !important; margin:1.1rem 0 .45rem !important; }
        h3 { font-size:.98rem !important; }
        .st-key-command-header { border-bottom:1px solid var(--line); margin-bottom:.55rem; padding-bottom:.3rem; }
        .st-key-command-header [data-testid="stCaption"] { color:var(--muted); }
        [data-testid="stMetric"] { background:var(--panel-raised); border:1px solid var(--line); border-radius:10px; min-height:86px; padding:.55rem .7rem; box-shadow:none; }
        [data-testid="stMetricLabel"] { color:var(--muted); font-size:.66rem; text-transform:uppercase; letter-spacing:.055em; }
        [data-testid="stMetricValue"] { color:var(--ink); font-size:1.2rem; font-weight:650; }
        [data-testid="stMetricDelta"] { color:var(--cyan); }
        .st-key-kpi-strip { background:var(--panel); border-color:var(--line); margin:.35rem 0 .75rem; padding:.22rem .35rem; }
        .st-key-kpi-strip [data-testid="stMetric"] { background:transparent; border:0; min-height:65px; padding:.35rem .5rem; }
        [data-testid="stSegmentedControl"] { margin:.45rem 0 .85rem; }
        [data-testid="stSegmentedControl"] button { font-size:.82rem; font-weight:600; }
        [data-testid="stVerticalBlockBorderWrapper"] { background:var(--panel); border-color:var(--line); border-radius:12px; }
        .section-caption { color:var(--muted); font-size:.82rem; margin-top:-.35rem; margin-bottom:.75rem; }
        .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:.9rem 1rem; }
        .eyebrow { color:var(--cyan); font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
        .assistant { background:var(--panel-raised); border:1px solid var(--line); border-radius:12px; padding:1rem 1.15rem; }
        .assistant-title { color:var(--ink); font-size:1.12rem; font-weight:650; }
        .assistant-copy { color:var(--muted); font-size:.84rem; margin:.35rem 0 .35rem; }
        .stButton > button { border:1px solid #304b68; border-radius:8px; font-weight:600; }
        .stButton > button:hover { border-color:var(--cyan); }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
        [data-baseweb="select"], [data-testid="stDateInput"], [data-testid="stNumberInput"], [data-testid="stTextInput"] { border-radius:8px; }
        [data-testid="stChatMessage"] { border:1px solid rgba(38,58,82,.75); border-radius:12px; background:rgba(17,30,48,.55); padding:.9rem 1rem; }
        @media (max-width: 900px) { [data-testid="stAppViewContainer"] > .main .block-container { padding:.8rem .8rem 1.5rem; } h1 { font-size:1.4rem !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
