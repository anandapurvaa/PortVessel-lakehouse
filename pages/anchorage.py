import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, dcc, html

from components.charts import (
    anchorage_dwell_distribution_figure,
    top_anchorage_dwell_figure,
)
from components.layout import empty_state, kpi_card, page_header, section_card
from data.repository import get_anchorage_dwells


dash.register_page(
    __name__,
    path="/anchorage",
    name="Anchorage",
    title="Port Vessel | Anchorage",
)


TABLE_COLUMNS = [
    {"name": "Vessel name", "id": "vessel_name"},
    {"name": "IMO", "id": "imo"},
    {"name": "Anchorage zone", "id": "zone_name"},
    {"name": "Entered (UTC)", "id": "anchorage_entered_at_utc"},
    {"name": "Exited (UTC)", "id": "anchorage_exited_at_utc"},
    {"name": "Dwell (hours)", "id": "anchorage_dwell_hours"},
    {"name": "Quality", "id": "anchorage_dwell_quality_status"},
]


def _display_table(df, limit=100):
    """Return a browser-safe, compact payload for the operational detail table."""
    if df.empty:
        return []

    columns = [
        "vessel_name",
        "imo",
        "zone_name",
        "anchorage_entered_at_utc",
        "anchorage_exited_at_utc",
        "anchorage_dwell_hours",
        "anchorage_dwell_quality_status",
    ]
    display = df[columns].head(limit).copy()

    for column, fallback in [
        ("vessel_name", "Unknown vessel"),
        ("imo", "—"),
        ("zone_name", "Unknown anchorage"),
        ("anchorage_dwell_quality_status", "unknown"),
    ]:
        display[column] = display[column].fillna(fallback).astype(str)

    for column in ["anchorage_entered_at_utc", "anchorage_exited_at_utc"]:
        display[column] = pd.to_datetime(
            display[column], utc=True, errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M UTC")
        display[column] = display[column].fillna("—")

    display["anchorage_dwell_hours"] = pd.to_numeric(
        display["anchorage_dwell_hours"], errors="coerce"
    ).map(lambda value: "—" if pd.isna(value) else f"{float(value):.1f}")

    return display.to_dict("records")


def _graph(figure, height=320):
    return html.Div(
        className="anchorage-chart-wrapper",
        style={"height": f"{height}px", "width": "100%"},
        children=dcc.Graph(
            figure=figure,
            config={"displayModeBar": False},
            responsive=False,
            style={"height": "100%", "width": "100%"},
        ),
    )


def layout():
    dwells = get_anchorage_dwells().copy()

    observed = dwells.loc[
        dwells["anchorage_dwell_quality_status"].eq("observed")
    ].copy()
    observed_count = len(observed)

    median_hours = (
        pd.to_numeric(observed["anchorage_dwell_hours"], errors="coerce").median()
        if observed_count
        else None
    )

    top_dwells = (
        observed
        .dropna(subset=["anchorage_dwell_hours"])
        .sort_values("anchorage_dwell_hours", ascending=False)
        .head(5)
        .copy()
    )

    dwell_distribution_chart = (
        _graph(anchorage_dwell_distribution_figure(observed))
        if observed_count
        else empty_state(
            "No observed anchorage dwell data",
            "No fully observed anchorage intervals are currently available.",
        )
    )

    top_dwells_chart = (
        _graph(top_anchorage_dwell_figure(top_dwells))
        if not top_dwells.empty
        else empty_state(
            "No observed anchorage dwells",
            "No fully observed anchorage intervals are currently available.",
        )
    )

    table_content = (
        html.Div(
            className="anchorage-table-wrapper",
            children=dash_table.DataTable(
                id="anchorage-dwell-table",
                columns=TABLE_COLUMNS,
                data=_display_table(dwells, limit=100),
                page_action="native",
                page_current=0,
                page_size=12,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto", "width": "100%"},
                style_header={
                    "backgroundColor": "#F5F8FA",
                    "color": "#36505F",
                    "fontWeight": 700,
                    "border": "none",
                    "padding": "12px",
                },
                style_cell={
                    "backgroundColor": "#FFFFFF",
                    "color": "#213547",
                    "border": "none",
                    "borderBottom": "1px solid #E8EEF2",
                    "padding": "12px",
                    "fontFamily": "Inter, system-ui, sans-serif",
                    "fontSize": "13px",
                    "textAlign": "left",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "minWidth": "120px",
                },
                style_data_conditional=[
                    {
                        "if": {
                            "filter_query": '{anchorage_dwell_quality_status} = "observed"',
                            "column_id": "anchorage_dwell_quality_status",
                        },
                        "backgroundColor": "#E8F5EE",
                        "color": "#167A4D",
                        "fontWeight": 700,
                    },
                    {
                        "if": {
                            "filter_query": '{anchorage_dwell_quality_status} = "partial"',
                            "column_id": "anchorage_dwell_quality_status",
                        },
                        "backgroundColor": "#FFF5DC",
                        "color": "#AA6C00",
                        "fontWeight": 700,
                    },
                ],
            ),
        )
        if not dwells.empty
        else empty_state(
            "No anchorage dwell records",
            "No USLAX anchorage intervals were returned from fct_anchorage_dwell.",
        )
    )

    return dbc.Container(
        fluid=True,
        className="page-container",
        children=[
            page_header(
                "Anchorage Operations",
                "USLAX / WAITING & QUEUE CONDITIONS",
                "Monitor observed anchorage dwell, tail risk, and vessel-level waiting patterns outside the terminal estate.",
            ),
            dbc.Row(
                className="g-4 mb-4",
                children=[
                    dbc.Col(
                        kpi_card(
                            "Observed anchorage dwells",
                            f"{observed_count:,}",
                            "Fully observed anchorage intervals",
                            "bi-anchor",
                            "teal",
                            "Anchorage dwell is included only when the interval starts and ends within available AIS coverage.",
                        ),
                        xs=12,
                        md=6,
                    ),
                    dbc.Col(
                        kpi_card(
                            "Median anchorage wait",
                            "—" if pd.isna(median_hours) else f"{median_hours:.1f} h",
                            "Observed anchorage dwell sample",
                            "bi-hourglass-split",
                            "amber",
                            "Median observed time spent in an anchorage geofence.",
                        ),
                        xs=12,
                        md=6,
                    ),
                ],
            ),
            dbc.Row(
                className="g-4 mb-4",
                children=[
                    dbc.Col(
                        section_card(
                            "Anchorage dwell distribution",
                            "Observed dwell durations from 0.0–4.0 hours in eight 0.5-hour bands; longer dwells are excluded from this view.",
                            dwell_distribution_chart,
                            class_name="anchorage-visual-card",
                        ),
                        xs=12,
                        lg=6,
                    ),
                    dbc.Col(
                        section_card(
                            "Longest observed anchorage dwells",
                            "Top 5 fully observed anchorage intervals by dwell duration.",
                            top_dwells_chart,
                            class_name="anchorage-visual-card",
                        ),
                        xs=12,
                        lg=6,
                    ),
                ],
            ),
            section_card(
                "Anchorage dwell detail",
                "Latest 100 intervals. A dash in Dwell (hours) means the interval has insufficient evidence for a valid dwell duration.",
                table_content,
                class_name="anchorage-table-card",
            ),
        ],
    )
