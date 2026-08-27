import math

import pandas as pd
import plotly.graph_objects as go


COLORS = {
    "navy": "#0A2540",
    "teal": "#007C83",
    "aqua": "#35B9C5",
    "blue": "#3A6EA5",
    "amber": "#E8A317",
    "orange": "#E76F51",
    "red": "#C44536",
    "green": "#208A5B",
    "gray": "#7A8793",
    "grid": "#E7EDF2",
    "text": "#213547",
    "white": "#FFFFFF",
}


QUALITY_COLORS = {
    "observed": COLORS["green"],
    "partial": COLORS["amber"],
    "left_censored": COLORS["orange"],
    "right_censored": COLORS["red"],
    "both_censored": "#7E57C2",
    "invalid": COLORS["gray"],
}


def _numeric_values(df, column):
    if df.empty or column not in df.columns:
        return []

    values = pd.to_numeric(df[column], errors="coerce")
    return [None if pd.isna(value) else float(value) for value in values.tolist()]


def _date_values(df, column):
    if df.empty or column not in df.columns:
        return []

    values = pd.to_datetime(df[column], errors="coerce")
    return [None if pd.isna(value) else value.strftime("%Y-%m-%d") for value in values.tolist()]


def _customdata_column(df, column):
    return [[value] for value in _numeric_values(df, column)]


def _nice_tick_step(max_value, target_ticks=6):
    """Return a readable continuous-axis step such as 1, 2, 5, 10, or 20."""
    if not max_value or max_value <= 0:
        return 1

    raw_step = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude

    if normalized <= 1:
        nice_normalized = 1
    elif normalized <= 2:
        nice_normalized = 2
    elif normalized <= 5:
        nice_normalized = 5
    else:
        nice_normalized = 10

    return nice_normalized * magnitude


def apply_base_layout(fig, height=360, showlegend=True):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor=COLORS["white"],
        plot_bgcolor=COLORS["white"],
        font={
            "family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            "color": COLORS["text"],
        },
        margin={"l": 62, "r": 24, "t": 24, "b": 62},
        showlegend=showlegend,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "left",
            "x": 0,
        },
        hoverlabel={
            "bgcolor": COLORS["navy"],
            "font": {"color": COLORS["white"]},
        },
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["grid"],
        tickfont={"color": COLORS["gray"]},
        automargin=True,
    )

    fig.update_yaxes(
        gridcolor=COLORS["grid"],
        zeroline=False,
        tickfont={"color": COLORS["gray"]},
        title_standoff=10,
        automargin=True,
    )

    return fig


def daily_calls_figure(df):
    fig = go.Figure()
    x = _date_values(df, "metric_date")

    fig.add_trace(
        go.Scatter(
            x=x,
            y=_numeric_values(df, "detected_port_calls"),
            mode="lines+markers",
            name="Detected calls",
            line={"color": COLORS["teal"], "width": 3},
            marker={"size": 8},
            hovertemplate="%{x}<br>Detected calls: %{y:.0f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=_numeric_values(df, "complete_port_calls"),
            mode="lines+markers",
            name="Complete calls",
            line={"color": COLORS["navy"], "width": 3},
            marker={"size": 8},
            hovertemplate="%{x}<br>Complete calls: %{y:.0f}<extra></extra>",
        )
    )

    apply_base_layout(fig)
    fig.update_xaxes(type="category", tickangle=0, tickmode="array", tickvals=x, ticktext=x)
    fig.update_yaxes(title_text="Port calls", rangemode="tozero", tickformat=",d")
    return fig


def port_duration_figure(df):
    fig = go.Figure(
        go.Scatter(
            x=_date_values(df, "metric_date"),
            y=_numeric_values(df, "median_port_duration_hours"),
            mode="lines+markers",
            name="Median port duration",
            line={"color": COLORS["blue"], "width": 3},
            marker={"size": 8},
            customdata=_customdata_column(df, "complete_port_calls"),
            hovertemplate=(
                "%{x}<br>Median duration: %{y:.1f} h<br>"
                "Complete-call sample: %{customdata[0]:.0f}<extra></extra>"
            ),
        )
    )

    apply_base_layout(fig, showlegend=False)
    fig.update_xaxes(type="category", tickangle=0)
    fig.update_yaxes(title_text="Hours", rangemode="tozero", tickformat=".1f")
    return fig


def quality_stacked_figure(df):
    fig = go.Figure()
    x = _date_values(df, "metric_date")

    for column, label, status in [
        ("observed_port_calls", "Observed", "observed"),
        ("partial_calls", "Partial", "partial"),
        ("left_censored_calls", "Left censored", "left_censored"),
        ("right_censored_calls", "Right censored", "right_censored"),
        ("both_censored_calls", "Both censored", "both_censored"),
    ]:
        if column in df.columns:
            fig.add_trace(
                go.Bar(
                    x=x,
                    y=_numeric_values(df, column),
                    name=label,
                    marker_color=QUALITY_COLORS[status],
                    hovertemplate=f"%{{x}}<br>{label}: %{{y:.0f}}<extra></extra>",
                )
            )

    apply_base_layout(fig, height=370)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(type="category", tickangle=0)
    fig.update_yaxes(title_text="Port calls", rangemode="tozero", tickformat=",d")
    return fig


def anchorage_timeseries_figure(df):
    fig = go.Figure()
    x = _date_values(df, "entry_date")

    fig.add_trace(
        go.Scatter(
            x=x,
            y=_numeric_values(df, "median_anchorage_dwell_hours"),
            mode="lines+markers",
            name="Median dwell",
            line={"color": COLORS["teal"], "width": 3},
            marker={"size": 8},
            hovertemplate="%{x}<br>Median dwell: %{y:.1f} h<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=_numeric_values(df, "p90_anchorage_dwell_hours"),
            mode="lines+markers",
            name="P90 dwell",
            line={"color": COLORS["amber"], "width": 3, "dash": "dash"},
            marker={"size": 8},
            hovertemplate="%{x}<br>P90 dwell: %{y:.1f} h<extra></extra>",
        )
    )

    apply_base_layout(fig, height=320)
    fig.update_xaxes(type="category", tickangle=-35, tickmode="array", tickvals=x, ticktext=x)
    fig.update_yaxes(title_text="Hours", rangemode="tozero", tickformat=".1f")
    return fig


def anchorage_dwell_distribution_figure(df):
    """Observed dwell distribution from 0.0 up to 4.0 hours in 0.5-hour bins."""
    dwell_hours = [
        value
        for value in _numeric_values(df, "anchorage_dwell_hours")
        if value is not None and 0 <= value <= 4.0
    ]

    fig = go.Figure()

    if not dwell_hours:
        apply_base_layout(fig, height=320, showlegend=False)
        fig.update_xaxes(
            title_text="Observed anchorage dwell (hours)",
            range=[0, 4],
            tickmode="linear",
            dtick=0.5,
            tickformat=".1f",
        )
        fig.update_yaxes(title_text="Observed intervals", rangemode="tozero", tickformat=",d")
        return fig

    fig.add_trace(
        go.Histogram(
            x=dwell_hours,
            xbins={"start": 0, "end": 4, "size": 0.5},
            marker={
                "color": COLORS["teal"],
                "line": {"color": COLORS["white"], "width": 1},
            },
            hovertemplate=(
                "Dwell band: %{x:.1f} h<br>"
                "Observed intervals: %{y:.0f}<extra></extra>"
            ),
        )
    )

    apply_base_layout(fig, height=320, showlegend=False)
    fig.update_xaxes(
        title_text="Observed anchorage dwell (hours)",
        range=[0, 4],
        tickmode="linear",
        dtick=0.5,
        tickformat=".1f",
    )
    fig.update_yaxes(
        title_text="Observed intervals",
        rangemode="tozero",
        tickformat=",d",
    )
    return fig


def anchorage_histogram_figure(df):
    """Backward-compatible alias for the bounded 0.0–4.0 hour distribution."""
    return anchorage_dwell_distribution_figure(df)


def top_anchorage_dwell_figure(df):
    """Ranked horizontal bars for the five longest fully observed dwell intervals."""
    if df.empty:
        figure = go.Figure()
        apply_base_layout(figure, height=320, showlegend=False)
        return figure

    ranked = df.copy()
    ranked["anchorage_dwell_hours"] = pd.to_numeric(
        ranked["anchorage_dwell_hours"], errors="coerce"
    )
    ranked = ranked.dropna(subset=["anchorage_dwell_hours"])
    ranked = ranked.sort_values("anchorage_dwell_hours", ascending=True).tail(5)

    vessel_labels = []
    for _, row in ranked.iterrows():
        vessel_name = row.get("vessel_name")
        vessel_labels.append(
            str(vessel_name) if pd.notna(vessel_name) else "Unknown vessel"
        )

    entered = pd.to_datetime(
        ranked.get("anchorage_entered_at_utc"), utc=True, errors="coerce"
    )
    exited = pd.to_datetime(
        ranked.get("anchorage_exited_at_utc"), utc=True, errors="coerce"
    )

    customdata = []
    for enter_time, exit_time in zip(entered, exited):
        enter_text = "—" if pd.isna(enter_time) else enter_time.strftime("%Y-%m-%d %H:%M UTC")
        exit_text = "—" if pd.isna(exit_time) else exit_time.strftime("%Y-%m-%d %H:%M UTC")
        customdata.append([enter_text, exit_text])

    figure = go.Figure(
        go.Bar(
            x=ranked["anchorage_dwell_hours"].tolist(),
            y=vessel_labels,
            orientation="h",
            marker={"color": COLORS["teal"]},
            customdata=customdata,
            hovertemplate=(
                "%{y}<br>Observed dwell: %{x:.1f} h<br>"
                "Entered: %{customdata[0]}<br>"
                "Exited: %{customdata[1]}<extra></extra>"
            ),
        )
    )

    apply_base_layout(figure, height=320, showlegend=False)
    max_hours = float(ranked["anchorage_dwell_hours"].max())
    tick_step = _nice_tick_step(max_hours, target_ticks=6)

    figure.update_xaxes(
        title_text="Observed dwell (hours)",
        range=[0, max_hours * 1.08 if max_hours > 0 else 1],
        tickmode="linear",
        dtick=tick_step,
        tickformat=".0f",
    )
    figure.update_yaxes(
        title_text="Vessel",
        tickfont={"size": 10, "color": COLORS["gray"]},
        automargin=True,
    )
    figure.update_layout(margin={"l": 155, "r": 24, "t": 24, "b": 52})
    return figure
