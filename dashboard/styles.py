import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root { --ink:#e8eef8; --muted:#91a0b5; --navy:#09111f; --panel:#111d2d; --panel-2:#16243a; --line:#22344c; --blue:#5b8def; --cyan:#55c7d9; --green:#4bd19b; --amber:#f2b866; }
        .stApp { background: radial-gradient(circle at 80% -10%, #1a3150 0, transparent 38%), var(--navy); color:var(--ink); font-family:'DM Sans', sans-serif; }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stAppViewContainer"] > .main { padding:1.2rem 2.4rem 2.5rem; }
        [data-testid="stSidebar"] { background:#0c1727; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding:1.4rem 1.1rem; }
        h1,h2,h3 { font-family:'Space Grotesk', sans-serif !important; letter-spacing:0 !important; color:var(--ink) !important; }
        h1 { font-size:2.1rem !important; margin:0 !important; }
        h2 { font-size:1.35rem !important; margin:1.6rem 0 .7rem !important; }
        h3 { font-size:1rem !important; }
        [data-testid="stMetric"] { background:linear-gradient(145deg, #15243a, #101b2c); border:1px solid var(--line); border-radius:14px; padding:1rem 1.05rem; min-height:125px; box-shadow:0 12px 30px rgba(0,0,0,.16); }
        [data-testid="stMetricLabel"] { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; }
        [data-testid="stMetricValue"] { color:var(--ink); font-family:'Space Grotesk',sans-serif; font-size:1.55rem; }
        [data-testid="stMetricDelta"] { color:var(--cyan); }
        .brand-kicker { color:var(--blue); font-size:.72rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; margin-bottom:.3rem; }
        .brand-subtitle { color:var(--muted); font-size:.95rem; margin-bottom:.2rem; }
        .status { color:#9ee8c7; font-size:.78rem; font-weight:600; display:flex; gap:.42rem; align-items:center; }
        .status-dot { background:var(--green); border-radius:50%; box-shadow:0 0 0 4px rgba(75,209,155,.12); display:inline-block; height:8px; width:8px; }
        .status-offline { color:#f2a4a4; } .status-offline .status-dot { background:#e57474; }
        .section-caption { color:var(--muted); font-size:.83rem; margin-top:-.45rem; margin-bottom:.9rem; }
        .panel { background:rgba(17,29,45,.78); border:1px solid var(--line); border-radius:14px; padding:1.05rem 1.1rem; }
        .eyebrow { color:var(--blue); font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
        .insight { border-left:3px solid var(--cyan); background:#122238; border-radius:0 10px 10px 0; color:#c7d4e6; padding:.72rem .9rem; font-size:.82rem; }
        .assistant { background:linear-gradient(120deg,#152944,#122238); border:1px solid #2c4f74; border-radius:16px; padding:1.2rem 1.35rem; }
        .assistant-title { color:var(--ink); font-family:'Space Grotesk'; font-size:1.1rem; font-weight:600; }
        .assistant-copy { color:var(--muted); font-size:.83rem; margin:.35rem 0 .8rem; }
        .footer { border-top:1px solid var(--line); color:#6f8097; font-size:.76rem; margin-top:2.2rem; padding-top:1rem; text-align:center; }
        .sidebar-label { color:#71849d; font-size:.68rem; font-weight:700; letter-spacing:.14em; margin:1.1rem 0 .35rem; text-transform:uppercase; }
        .stButton > button { border:1px solid #2b4667; border-radius:8px; color:#dbe8f7; background:#13253d; font-weight:600; }
        .stButton > button:hover { border-color:var(--blue); color:white; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
        [data-baseweb="select"], [data-testid="stDateInput"] { border-radius:8px; }
        @media (max-width: 900px) { [data-testid="stAppViewContainer"] > .main { padding:1rem; } h1 { font-size:1.7rem !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )