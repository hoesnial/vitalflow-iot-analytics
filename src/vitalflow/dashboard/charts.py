"""Chart constructors that preserve units, counts, and missing observations."""

import pandas as pd
import plotly.graph_objects as go

from .analysis import CHANNELS, series_with_gaps
from .design import AMBER, CHANNEL_COLORS, CYAN


def window_trend(frame: pd.DataFrame, channel: str, step: float) -> go.Figure:
    channel_info = CHANNELS[channel]
    ordered = frame.sort_values("window_start_s")
    steps = ordered["window_start_s"]
    # Match missing window breaks to a null point even when the window is absent.
    x, y, _ = series_with_gaps(steps, ordered[f"{channel}_mean"], step)
    totals = ordered.set_index("window_start_s")[["rows", f"{channel}_valid"]].to_dict("index")
    counts = [
        [totals.get(t, {}).get(f"{channel}_valid", 0), totals.get(t, {}).get("rows", 0)] for t in x
    ]
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            customdata=counts,
            name=channel_info.label,
            mode="lines+markers",
            connectgaps=False,
            line={"color": CHANNEL_COLORS[channel], "width": 2.4},
            marker={"size": 6},
            hovertemplate=(
                f"%{{x:.0f}} s · %{{y:.2f}} {channel_info.unit}"
                "<br>Valid: %{customdata[0]} / %{customdata[1]}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title="Awal jendela (detik)")
    fig.update_yaxes(title=channel_info.unit)
    return fig


def raw_trend(
    frame: pd.DataFrame, channels: tuple[str, ...], cadence: float, *, markers: bool = False
) -> go.Figure:
    if not channels or len({CHANNELS[key].unit for key in channels}) != 1:
        raise ValueError("Only channels with the same unit can share a raw chart")
    fig = go.Figure()
    show_missing_lane = False
    for idx, key in enumerate(channels):
        channel = CHANNELS[key]
        x, y, missing = series_with_gaps(frame["time_s"], frame[key], cadence)
        fig.add_scatter(
            x=x,
            y=y,
            name=channel.label,
            mode="lines+markers",
            connectgaps=False,
            line={
                "color": CHANNEL_COLORS[key],
                "width": 2,
                "dash": "solid" if idx == 0 else "dash",
            },
            marker={"size": 3, "symbol": "circle" if idx == 0 else "diamond"},
            hovertemplate=f"%{{x:g}} s · %{{y:.2f}} {channel.unit}<extra>{channel.label}</extra>",
        )
        if markers and missing:
            show_missing_lane = True
            fig.add_scatter(
                x=missing,
                y=[0.34 + 0.38 * idx] * len(missing),
                yaxis="y2",
                name=f"{channel.label} hilang",
                mode="markers",
                marker={
                    "symbol": "line-ns",
                    "size": 8,
                    "color": AMBER,
                    "line": {"width": 1.4, "color": AMBER},
                },
                hovertemplate=f"%{{x:g}} s · tidak ada nilai<extra>{channel.label}</extra>",
            )
    if show_missing_lane:
        fig.update_layout(
            yaxis={"domain": [0.17, 1]},
            yaxis2={"domain": [0, 0.12], "range": [0, 1], "visible": False, "fixedrange": True},
            xaxis={"anchor": "y2"},
        )
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0,
            y=0.045,
            xanchor="right",
            xshift=-4,
            text="Hilang",
            showarrow=False,
            font={"color": AMBER, "size": 11},
        )
    fig.update_layout(xaxis_title="Waktu rekaman (detik)", yaxis_title=CHANNELS[channels[0]].unit)
    return fig


def missing_bars(missing: dict[str, int]) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=list(missing.values()),
            y=[CHANNELS[key].label for key in missing],
            orientation="h",
            marker_color=AMBER,
            text=list(missing.values()),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x} sel hilang<extra></extra>",
        )
    )
    fig.update_xaxes(
        title="Sel hilang",
        rangemode="tozero",
        range=[0, max(1, max(missing.values()) * 1.23)],
        dtick=1 if max(missing.values()) < 4 else None,
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def recording_bars(frame: pd.DataFrame, channel: str) -> go.Figure:
    info = CHANNELS[channel]
    fig = go.Figure(
        go.Bar(
            x=frame["recording_id"].tolist(),
            y=frame[f"{channel}_mean"].tolist(),
            customdata=frame[[f"{channel}_valid", "rows"]].values.tolist(),
            marker_color=CYAN,
            hovertemplate=f"%{{x}} · %{{y:.2f}} {info.unit}<br>Valid %{{customdata[0]}} / %{{customdata[1]}}<extra></extra>",
        )
    )
    fig.update_xaxes(title="Recording ID", nticks=12, type="category", tickangle=-35)
    fig.update_yaxes(title=info.unit, rangemode="tozero")
    return fig
