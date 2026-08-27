import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from components.charts import (
    daily_calls_figure,
    port_duration_figure,
    quality_stacked_figure,
)
from components.layout import empty_state, kpi_card, page_header, section_card
from data.repository import get_daily_congestion


dash.register_page(__name__, path="/", name="Overview", title="Port Vessel | Overview")


def _format_integer(value):
    if value is None:
        return "—"
    return f"{int(value):,}"


def _format_hours(value):
    if value is None:
        return "—"
    return f"{value:.1f} h"


def _has_chart_data(df, required_columns):
    return (
        not df.empty
        and all(column in df.columns for column in required_columns)
        and not df[required_columns].dropna(how="all").empty
    )


def _graph(figure, height=360):
    return html.Div(
        className="overview-chart-wrapper",
        style={"height": f"{height}px", "width": "100%"},
        children=dcc.Graph(
            figure=figure,
            config={"displayModeBar": False},
            responsive=False,
            style={"height": "100%", "width": "100%"},
        ),
    )


def layout():
    daily = get_daily_congestion().copy()

    total_calls = daily["detected_port_calls"].sum() if not daily.empty else 0
    total_vessels = daily["detected_vessels"].sum() if not daily.empty else 0
    total_complete = daily["complete_port_calls"].sum() if not daily.empty else 0

    duration_series = (
        daily["median_port_duration_hours"].dropna()
        if "median_port_duration_hours" in daily.columns
        else []
    )
    median_duration = duration_series.median() if len(duration_series) else None
    coverage = total_complete / total_calls if total_calls else 0

    calls_chart = (
        _graph(daily_calls_figure(daily), height=360)
        if _has_chart_data(
            daily,
            ["metric_date", "detected_port_calls", "complete_port_calls"],
        )
        else empty_state(
            "No daily call data",
            "Run the dbt Gold marts and refresh the dashboard.",
        )
    )

    duration_chart = (
        _graph(port_duration_figure(daily), height=360)
        if _has_chart_data(daily, ["metric_date", "median_port_duration_hours"])
        else empty_state(
            "No complete duration data",
            "No fully observed port calls are available yet.",
        )
    )

    quality_chart = (
        _graph(quality_stacked_figure(daily), height=370)
        if _has_chart_data(daily, ["metric_date", "observed_port_calls"])
        else empty_state(
            "No quality-status data",
            "Run the dbt Gold marts and refresh the dashboard.",
        )
    )

    return dbc.Container(
        fluid=True,
        className="page-container",
        children=[
            page_header(
                "Port Congestion Overview",
                "USLAX / OPERATIONAL SNAPSHOT",
                "A quality-aware view of vessel activity, observed turnaround time, and AIS data coverage.",
            ),
            dbc.Row(
                className="g-4 mb-4",
                children=[
                    dbc.Col(
                        kpi_card(
                            "Total detected port calls",
                            _format_integer(total_calls),
                            "All detected in-port sequences",
                            "bi-water",
                            "teal",
                            "Includes observed, partial, and censored port-call sequences.",
                        ),
                        xs=12,
                        sm=6,
                        xl=3,
                    ),
                    dbc.Col(
                        kpi_card(
                            "Total detected vessels",
                            _format_integer(total_vessels),
                            "Distinct vessel-day observations",
                            "bi-ship",
                            "navy",
                            "Counts distinct AIS vessels represented in the daily operational dataset.",
                        ),
                        xs=12,
                        sm=6,
                        xl=3,
                    ),
                    dbc.Col(
                        kpi_card(
                            "Complete port calls",
                            _format_integer(total_complete),
                            f"{coverage:.0%} eligible for duration KPIs",
                            "bi-check2-circle",
                            "green",
                            "Only calls with a fully observed arrival-to-departure period qualify.",
                        ),
                        xs=12,
                        sm=6,
                        xl=3,
                    ),
                    dbc.Col(
                        kpi_card(
                            "Median port duration",
                            _format_hours(median_duration),
                            "Fully observed calls only",
                            "bi-clock-history",
                            "amber",
                            "Median arrival-to-departure duration among complete port calls.",
                        ),
                        xs=12,
                        sm=6,
                        xl=3,
                    ),
                ],
            ),
            dbc.Row(
                className="g-4 mb-4",
                children=[
                    dbc.Col(
                        section_card(
                            "Detected vs complete calls",
                            "Daily volume and the eligible sample for turnaround-time metrics",
                            calls_chart,
                            class_name="overview-visual-card",
                        ),
                        xs=12,
                        lg=6,
                    ),
                    dbc.Col(
                        section_card(
                            "Median port duration",
                            "Hours; calculated only from fully observed calls",
                            duration_chart,
                            class_name="overview-visual-card",
                        ),
                        xs=12,
                        lg=6,
                    ),
                ],
            ),
            dbc.Row(
                className="g-4",
                children=[
                    dbc.Col(
                        section_card(
                            "Port-call observation quality",
                            "Call counts by daily quality classification",
                            quality_chart,
                            class_name="overview-quality-card",
                        ),
                        lg=8,
                    ),
                    dbc.Col(
                        dbc.Card(
                            className="coverage-card",
                            children=dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.Div("DATA COVERAGE", className="eyebrow"),
                                            html.H4("Quality interpretation", className="coverage-title"),
                                        ]
                                    ),
                                    html.Div(className="coverage-number", children=f"{coverage:.0%}"),
                                    html.P(
                                        "of detected calls are eligible for full port-duration metrics across the selected data scope.",
                                        className="coverage-copy",
                                    ),
                                    html.Hr(),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Span(className="legend-dot green"),
                                                    html.Span("Observed: complete duration"),
                                                ],
                                                className="quality-legend-item",
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(className="legend-dot amber"),
                                                    html.Span("Partial: insufficient interval evidence"),
                                                ],
                                                className="quality-legend-item",
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(className="legend-dot red"),
                                                    html.Span("Censored: source-window boundary"),
                                                ],
                                                className="quality-legend-item",
                                            ),
                                        ]
                                    ),
                                    dbc.Alert(
                                        "Use the complete-call and observed-dwell sample counts shown with each KPI when interpreting daily trends.",
                                        color="info",
                                        className="coverage-alert",
                                    ),
                                ]
                            ),
                        ),
                        lg=4,
                    ),
                ],
            ),
        ],
    )
