"""VitalFlow visual tokens, typography, and compact Streamlit components."""

from base64 import b64encode
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BG, SIDEBAR, SURFACE, RAISED = "#08111F", "#0C1728", "#111F32", "#17283D"
TEXT, MUTED, BORDER = "#F1F5F9", "#94A3B8", "#263950"
CYAN, TEAL, AMBER, RED = "#38BDF8", "#2DD4BF", "#FBBF24", "#FB7185"
FONT = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
CHANNEL_COLORS = {"hr": CYAN, "pulse": TEAL, "resp": "#A5B4FC", "spo2": "#F0ABFC"}

MARK = """<svg width="23" height="23" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M2 12h5l2.8-6 3.8 12 2.8-6H22" stroke="#38BDF8" stroke-width="1.7"
stroke-linecap="round" stroke-linejoin="round"/></svg>"""

STYLE = """
<style>
:root {{
  --vf-bg:{bg}; --vf-sidebar:{sidebar}; --vf-surface:{surface}; --vf-raised:{raised};
  --vf-text:{text}; --vf-muted:{muted}; --vf-border:{border}; --vf-cyan:{cyan};
  --vf-teal:{teal}; --vf-amber:{amber}; --vf-font:{font};
}}
.stApp {{background:var(--vf-bg); color:var(--vf-text);}}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp p, [data-testid=stMetricValue] {{
  font-family:var(--vf-font);
}}
[data-testid=stHeader] {{background:transparent; pointer-events:none;}}
[data-testid=stAppDeployButton] {{display:none;}}
[data-testid=stToolbar] {{pointer-events:auto;}}
[data-testid=stToolbar] {{right:1.25rem;}}
[data-testid=stSidebar] {{background:var(--vf-sidebar); border-right:1px solid #1b2a3d;}}
[data-testid=stSidebarContent] {{min-width:0;}}
[data-testid=stSidebarUserContent] {{padding-top:1.45rem;}}
[data-testid=stMainBlockContainer] {{padding:3.1rem 2.1rem 2.25rem; max-width:1520px;}}
[data-testid=stMainBlockContainer] [data-testid=stVerticalBlock] {{gap:.88rem;}}
[data-testid=stHorizontalBlock] {{gap:.82rem;}}
[data-testid=stSidebar] [role=radiogroup] {{gap:.24rem;}}
[data-testid=stSidebar] [role=radiogroup] label {{
  padding:.52rem .58rem; border-radius:.45rem; margin:0; width:100%; min-height:2.5rem;
}}
[data-testid=stSidebar] [role=radiogroup] label:has(input:checked) {{
  background:#142b43; box-shadow:inset 2px 0 var(--vf-cyan);
}}
[data-testid=stSidebar] [role=radiogroup] label:hover {{background:var(--vf-raised);}}
[data-testid=stSidebar] [role=radiogroup] label:has(input:focus-visible) {{
  outline:2px solid var(--vf-cyan); outline-offset:2px;
}}
[data-testid=stSidebar] [role=radiogroup] p {{font-size:.87rem; font-weight:570;}}
[data-testid=stMetric] {{background:var(--vf-surface); border:1px solid #22354c; border-radius:.65rem;
  padding:.65rem .82rem !important; min-height:5.25rem;}}
[data-testid=stMetricLabel] p {{font-size:.80rem; color:var(--vf-muted);}}
[data-testid=stMetricValue] {{
  color:var(--vf-text); font-size:clamp(1.26rem,2.15vw,1.9rem);
  font-variant-numeric:tabular-nums; font-weight:680; letter-spacing:-.038em;
}}
[data-testid=stVerticalBlockBorderWrapper] > div {{min-width:0;}}
[class*="st-key-panel_"] {{background:var(--vf-surface); border-color:#22354c !important;}}
.stMarkdown h2 {{font-size:1.32rem; letter-spacing:-.026em;}}
.stMarkdown h3 {{font-size:1.05rem; letter-spacing:-.02em;}}
.stMarkdown p {{text-wrap:pretty;}}
.stCaption p {{color:var(--vf-muted); font-size:.80rem;}}
[data-testid=stButton] button, [data-testid=stDownloadButton] button {{min-height:2.45rem;}}
[data-testid=stAlert] p {{font-size:.90rem;}}
.vf-brand {{display:flex; align-items:center; gap:.72rem; padding-bottom:.65rem;}}
.vf-mark {{display:grid; place-items:center; width:37px; height:37px; flex:0 0 37px;
  border-radius:.58rem; color:var(--vf-cyan); background:#102f46; border:1px solid #214761;}}
.vf-wordmark {{font-size:1.11rem; font-weight:760; line-height:1.22; letter-spacing:-.033em;}}
.vf-subbrand {{font-size:.66rem; color:var(--vf-muted); font-weight:650; letter-spacing:.07em;}}
.vf-label {{color:var(--vf-cyan); text-transform:uppercase; font-size:.70rem;
  font-weight:750; letter-spacing:.12em;}}
.vf-head {{padding:.15rem 0 .15rem;}}
.vf-head h1 {{font-size:clamp(1.85rem,3.0vw,2.8rem); line-height:1.06;
  letter-spacing:-.052em; margin:.33rem 0 .44rem; padding:0; text-wrap:balance;}}
.vf-head p {{color:var(--vf-muted); font-size:.91rem; margin:0; max-width:72ch;}}
.vf-hero {{background:var(--vf-surface); border:1px solid #263b53;
  border-left:3px solid var(--vf-cyan); border-radius:.70rem; padding:.78rem 1.2rem .83rem;}}
.vf-hero-meta {{display:flex; flex-wrap:wrap; justify-content:space-between; gap:.28rem .85rem;}}
.vf-tagline {{font-size:.71rem; color:var(--vf-muted);}}
.vf-hero h1 {{font-size:clamp(2.35rem,4vw,3.08rem);}}
.vf-hero strong {{display:block; font-size:1.05rem; font-weight:620; color:var(--vf-text);}}
.vf-hero p {{margin-top:.20rem;}}
.vf-badges {{display:flex; flex-wrap:wrap; gap:.37rem; margin-top:.53rem;}}
.vf-badge {{font-size:.69rem; font-weight:650; line-height:1.38; border-radius:4rem;
  padding:.23rem .55rem; border:1px solid var(--vf-border); color:var(--vf-muted);}}
.vf-badge--source {{background:#103431; color:#83EBDD; border-color:#23534e;}}
.vf-badge--replay {{background:#312719; color:#f8d887; border-color:#53432d;}}
.vf-panelhead h2 {{font-size:1.12rem; line-height:1.28; font-weight:690;
  letter-spacing:-.023em; margin:.03rem 0 .12rem; padding:0;}}
.vf-panelhead p {{color:var(--vf-muted); font-size:.77rem; margin:0;}}
.vf-meta {{color:var(--vf-muted); font-size:.76rem; line-height:1.55;}}
.vf-meta strong {{color:var(--vf-text);}}
.vf-ledger {{border-top:1px solid var(--vf-border); margin-top:.20rem; padding-top:.58rem;
  display:grid; gap:.32rem;}}
.vf-ledger span {{font-size:.79rem; line-height:1.42; color:var(--vf-muted);}}
.vf-ledger strong {{color:var(--vf-teal); font-weight:680;}}
.vf-vitem {{min-height:4.6rem;}}
.vf-vitem strong {{display:block; color:var(--vf-text); margin-top:.24rem;}}
.vf-vitem p {{color:var(--vf-muted); font-size:.78rem; margin:.23rem 0 0;}}
.vf-strip {{background:var(--vf-surface); border-left:2px solid var(--vf-teal);
  border-radius:.45rem; padding:.76rem .85rem; color:var(--vf-text); font-size:.88rem;}}
.st-key-preview_channel [role=radiogroup] label {{
  border:1px solid var(--vf-border); border-radius:.45rem; padding:.27rem .46rem;
}}
.st-key-preview_channel [role=radiogroup] label:has(input:checked) {{
  background:#142b43; border-color:var(--vf-cyan);
}}
.st-key-preview_channel [role=radiogroup] label p {{font-size:.79rem;}}
.vf-join {{display:grid; grid-template-columns:1fr 1fr auto 1.3fr; gap:.55rem; align-items:center;}}
.vf-join div {{min-width:0; padding:.66rem; border:1px solid var(--vf-border); border-radius:.45rem;}}
.vf-join small {{display:block; color:var(--vf-muted);}}
.vf-join > span {{color:var(--vf-cyan); font-size:1.25rem;}}
.vf-flow img {{display:block; width:100%; height:auto;}}
.vf-flow-mobile {{display:none;}}
@media (max-width: 1120px) {{
  [data-testid=stMainBlockContainer] {{padding-left:1.28rem; padding-right:1.28rem;}}
}}
@media (max-width: 760px) {{
  [data-testid=stMainBlockContainer] {{padding:3.1rem .82rem 1.45rem;}}
  [data-testid=stMetric] {{min-height:4.8rem;}}
  .vf-flow img {{display:none;}}
  .vf-join {{grid-template-columns:1fr;}}
  .vf-join > span {{transform:rotate(90deg); justify-self:center;}}
  .vf-flow-mobile {{display:block; padding-left:1.3rem;}}
  .vf-flow-mobile li {{padding:.22rem 0;}}
}}
</style>
""".format(
    bg=BG,
    sidebar=SIDEBAR,
    surface=SURFACE,
    raised=RAISED,
    text=TEXT,
    muted=MUTED,
    border=BORDER,
    cyan=CYAN,
    teal=TEAL,
    amber=AMBER,
    font=FONT,
)


def apply_style() -> None:
    st.html(STYLE)


def brand() -> None:
    mark = b64encode(MARK.encode()).decode()
    st.html(
        f'<div class="vf-brand"><div class="vf-mark"><img alt="" width="23" height="23" '
        f'src="data:image/svg+xml;base64,{mark}"></div><div>'
        '<div class="vf-wordmark">VitalFlow</div><div class="vf-subbrand">'
        "ANALITIK BIG DATA</div></div></div>"
    )


def page_head(kicker: str, title: str, subtitle: str) -> None:
    st.html(
        f'<header class="vf-head"><div class="vf-label">{escape(kicker)}</div>'
        f"<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></header>"
    )


def panel_head(title: str, subtitle: str = "") -> None:
    st.html(f'<div class="vf-panelhead"><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div>')


def strip(text: str) -> None:
    st.html(f'<div class="vf-strip">{escape(text)}</div>')


def fmt(value, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}".translate(str.maketrans(".,", ",."))


def plot(figure: go.Figure, key: str, height: int = 295, legend: bool = False) -> None:
    figure.update_layout(
        height=height,
        template="plotly_dark",
        font={"family": FONT, "color": TEXT, "size": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 48, "r": 18, "t": 26 if legend else 13, "b": 45},
        hoverlabel={"bgcolor": RAISED, "font": {"color": TEXT, "size": 13}},
        showlegend=legend,
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED, automargin=True)
    figure.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED, automargin=True)
    st.plotly_chart(
        figure,
        key=key,
        theme=None,
        width="stretch",
        config={
            "displaylogo": False,
            "scrollZoom": False,
            "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )


def table(rows, *, key: str | None = None, height: int | str = "auto", columns=None) -> None:
    st.dataframe(
        rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=height,
        key=key,
        column_config=columns,
    )
