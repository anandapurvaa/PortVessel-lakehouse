import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dash_table, dcc, html
from dash.exceptions import PreventUpdate

from components.layout import page_header, section_card
from data.repository import get_port_calls


dash.register_page(
    __name__,
    path="/port-calls",
    name="Port Calls",
    title="Port Vessel | Port Calls",
)


QUALITY_OPTIONS = [
    {"label": "Observed", "value": "observed"},
    {"label": "Partial", "value": "partial"},
    {"label": "Left censored", "value": "left_censored"},
    {"label": "Right censored", "value": "right_censored"},
    {"label": "Both censored", "value": "both_censored"},
    {"label": "Invalid", "value": "invalid"},
]


def _format_table(df):
    result = df.copy()

    for col in ["arrival_observed_at_utc", "departure_observed_at_utc"]:
        result[col] = pd.to_datetime(
            result[col],
            utc=True,
            errors="coerce",
        ).dt.strftime("%Y-%m-%d %H:%M UTC")
        result[col] = result[col].fillna("—")

    for col in [
        "port_duration_hours",
        "anchorage_wait_hours",
        "berth_dwell_hours",
    ]:
        result[col] = pd.to_numeric(
            result[col],
            errors="coerce",
        ).map(
            lambda value: "—" if pd.isna(value) else f"{float(value):.1f}"
        )

    for col in ["vessel_name", "mmsi", "port_call_quality_status"]:
        if col in result.columns:
            result[col] = result[col].fillna("—").astype(str)

    return result.to_dict("records")


def _initial_dates(df):
    dates = pd.to_datetime(df["arrival_date"], errors="coerce").dropna()

    if dates.empty:
        today = pd.Timestamp.today().date()
        return today, today

    return dates.min().date(), dates.max().date()


def layout():
    calls = get_port_calls()
    start_date, end_date = _initial_dates(calls)

    table_columns = [
        {"name": "Vessel name", "id": "vessel_name"},
        {"name": "MMSI", "id": "mmsi"},
        {"name": "Arrival (UTC)", "id": "arrival_observed_at_utc"},
        {"name": "Departure (UTC)", "id": "departure_observed_at_utc"},
        {"name": "Port duration (h)", "id": "port_duration_hours"},
        {"name": "Anchorage wait (h)", "id": "anchorage_wait_hours"},
        {"name": "Berth proximity (h)", "id": "berth_dwell_hours"},
        {"name": "Quality status", "id": "port_call_quality_status"},
    ]

    initial_calls = calls[
        calls["port_call_quality_status"].eq("observed")
    ].copy()

    return dbc.Container(
        fluid=True,
        className="page-container",
        children=[
            page_header(
                "Port Call Explorer",
                "USLAX / VESSEL MOVEMENTS",
                "Inspect vessel-level arrival, anchorage, berth-proximity, and observation-quality evidence.",
            ),
            section_card(
                "Filters",
                "The table defaults to fully observed calls. Enable other statuses to audit data coverage.",
                dbc.Row(
                    className="g-3 align-items-end",
                    children=[
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Arrival date range",
                                    className="filter-label",
                                ),
                                dcc.DatePickerRange(
                                    id="port-calls-date-range",
                                    start_date=start_date,
                                    end_date=end_date,
                                    min_date_allowed=start_date,
                                    max_date_allowed=end_date,
                                    display_format="YYYY-MM-DD",
                                    className="date-picker-control",
                                ),
                            ],
                            xs=12,
                            md=5,
                        ),
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Quality status",
                                    className="filter-label",
                                ),
                                dcc.Dropdown(
                                    id="port-calls-quality-filter",
                                    options=QUALITY_OPTIONS,
                                    value=["observed"],
                                    multi=True,
                                    clearable=False,
                                    className="quality-dropdown",
                                ),
                            ],
                            xs=12,
                            md=5,
                        ),
                        dbc.Col(
                            dbc.Button(
                                [
                                    html.I(className="bi bi-download me-2"),
                                    "Export CSV",
                                ],
                                id="port-calls-export-button",
                                color="primary",
                                className="export-button w-100",
                            ),
                            xs=12,
                            md=2,
                        ),
                    ],
                ),
                class_name="port-calls-filter-card",
            ),
            html.Div(className="section-spacer"),
            section_card(
                "Port call detail",
                "Durations are displayed in hours. An em dash indicates that the relevant duration is not fully observed.",
                [
                    dcc.Loading(
                        type="circle",
                        color="#007C83",
                        children=html.Div(
                            id="port-calls-table-container",
                            children=dash_table.DataTable(
                                id="port-calls-table",
                                columns=table_columns,
                                data=_format_table(initial_calls),
                                page_size=15,
                                sort_action="native",
                                filter_action="native",
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                },
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
                                            "filter_query": (
                                                '{port_call_quality_status} = "observed"'
                                            ),
                                            "column_id": "port_call_quality_status",
                                        },
                                        "backgroundColor": "#E8F5EE",
                                        "color": "#167A4D",
                                        "fontWeight": 700,
                                    },
                                    {
                                        "if": {
                                            "filter_query": (
                                                '{port_call_quality_status} = "partial"'
                                            ),
                                            "column_id": "port_call_quality_status",
                                        },
                                        "backgroundColor": "#FFF5DC",
                                        "color": "#AA6C00",
                                        "fontWeight": 700,
                                    },
                                    {
                                        "if": {
                                            "filter_query": (
                                                '{port_call_quality_status} contains "censored"'
                                            ),
                                            "column_id": "port_call_quality_status",
                                        },
                                        "backgroundColor": "#FCEBE8",
                                        "color": "#B13C31",
                                        "fontWeight": 700,
                                    },
                                ],
                            ),
                        ),
                    ),
                    dcc.Download(id="port-calls-download"),
                ],
                class_name="port-calls-table-card",
            ),
        ],
    )


def _filtered_calls(start_date, end_date, statuses):
    df = get_port_calls().copy()
    df["arrival_date"] = pd.to_datetime(
        df["arrival_date"],
        errors="coerce",
    ).dt.date

    if start_date:
        df = df[df["arrival_date"] >= pd.to_datetime(start_date).date()]

    if end_date:
        df = df[df["arrival_date"] <= pd.to_datetime(end_date).date()]

    if statuses:
        df = df[df["port_call_quality_status"].isin(statuses)]
    else:
        df = df.iloc[0:0]

    return df.sort_values("arrival_observed_at_utc", ascending=False)


@callback(
    Output("port-calls-table", "data"),
    Input("port-calls-date-range", "start_date"),
    Input("port-calls-date-range", "end_date"),
    Input("port-calls-quality-filter", "value"),
)
def update_port_calls_table(start_date, end_date, statuses):
    return _format_table(_filtered_calls(start_date, end_date, statuses))


@callback(
    Output("port-calls-download", "data"),
    Input("port-calls-export-button", "n_clicks"),
    Input("port-calls-date-range", "start_date"),
    Input("port-calls-date-range", "end_date"),
    Input("port-calls-quality-filter", "value"),
    prevent_initial_call=True,
)
def export_port_calls(n_clicks, start_date, end_date, statuses):
    if not n_clicks:
        raise PreventUpdate

    export_df = _filtered_calls(start_date, end_date, statuses).copy()

    for col in ["arrival_observed_at_utc", "departure_observed_at_utc"]:
        export_df[col] = pd.to_datetime(
            export_df[col],
            utc=True,
            errors="coerce",
        ).dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    return dcc.send_data_frame(
        export_df.to_csv,
        "uslax_port_calls.csv",
        index=False,
    )