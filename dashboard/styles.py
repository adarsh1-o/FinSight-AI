import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#e8eef8; --muted:#91a0b5; --navy:#08111f; --panel:#111e30; --line:#263a52; --blue:#69a7ff; --cyan:#4bc7d3; --green:#43c995; --amber:#f2b866; --coral:#f07878; }
        .stApp { background:radial-gradient(ellipse at 78% -12%, rgba(41,83,126,.23), transparent 40%), var(--navy); color:var(--ink); }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stAppViewContainer"] > .main .block-container { max-width:1680px; padding:1.5rem 2.35rem 3rem; }
        [data-testid="stSidebar"] { background:#0b1727; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding:1.4rem 1.05rem; }
        h1,h2,h3 { letter-spacing:-.025em !important; color:var(--ink) !important; }
        h1 { font-size:2.15rem !important; margin:0 !important; }
        h2 { font-size:1.28rem !important; margin:1.4rem 0 .55rem !important; }
        h3 { font-size:1rem !important; }
        [data-testid="stMetric"] { background:linear-gradient(145deg, #14243a, #101b2c); border:1px solid var(--line); border-radius:13px; min-height:116px; box-shadow:0 8px 24px rgba(0,0,0,.12); }
        [data-testid="stMetricLabel"] { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.065em; }
        [data-testid="stMetricValue"] { color:var(--ink); font-size:1.5rem; font-weight:650; }
        [data-testid="stMetricDelta"] { color:var(--cyan); }
        [role="tablist"] { border-bottom:1px solid var(--line); gap:.35rem; }
        [role="tab"] { border-radius:8px 8px 0 0; color:var(--muted); font-weight:600; padding:.65rem .9rem; }
        [role="tab"][aria-selected="true"] { background:rgba(75,199,211,.09); color:var(--cyan); }
        .brand-kicker { color:var(--cyan); font-size:.69rem; font-weight:700; letter-spacing:.15em; text-transform:uppercase; margin-bottom:.35rem; }
        .brand-subtitle { color:var(--muted); font-size:.94rem; margin:.28rem 0 .6rem; }
        .section-caption { color:var(--muted); font-size:.84rem; margin-top:-.35rem; margin-bottom:.85rem; }
        .panel { background:rgba(17,30,48,.78); border:1px solid var(--line); border-radius:13px; padding:1rem 1.1rem; }
        .eyebrow { color:var(--cyan); font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
        .assistant { background:linear-gradient(120deg,rgba(25,53,82,.85),rgba(17,30,48,.9)); border:1px solid #294763; border-radius:15px; padding:1.2rem 1.35rem; }
        .assistant-title { color:var(--ink); font-size:1.12rem; font-weight:650; }
        .assistant-copy { color:var(--muted); font-size:.84rem; margin:.35rem 0 .35rem; }
        .footer { border-top:1px solid var(--line); color:#74869d; font-size:.76rem; margin-top:2.2rem; padding-top:1rem; text-align:center; }
        .sidebar-label { color:#8395ac; font-size:.67rem; font-weight:700; letter-spacing:.12em; margin:1rem 0 .3rem; text-transform:uppercase; }
        .stButton > button { border:1px solid #304b68; border-radius:9px; font-weight:600; transition:border-color .15s ease, background .15s ease; }
        .stButton > button:hover { border-color:var(--cyan); }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
        [data-baseweb="select"], [data-testid="stDateInput"], [data-testid="stNumberInput"], [data-testid="stTextInput"] { border-radius:8px; }
        [data-testid="stChatMessage"] { border:1px solid rgba(38,58,82,.75); border-radius:12px; background:rgba(17,30,48,.55); padding:.9rem 1rem; }
        @media (max-width: 900px) { [data-testid="stAppViewContainer"] > .main .block-container { padding:1rem 1rem 2rem; } h1 { font-size:1.75rem !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
