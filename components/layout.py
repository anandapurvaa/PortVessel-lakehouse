from datetime import datetime, timezone

import dash_bootstrap_components as dbc
from dash import dcc, html


DATA_SCOPE_TEXT = (
    "Data scope: USLAX geofenced AIS observations from January 2024 onward. "
    "Port-duration metrics use only fully observed calls; anchorage and "
    "berth-proximity metrics use fully observed intervals for each respective metric."
)


NAV_ITEMS = [
    ("Overview", "/"),
    ("Anchorage", "/anchorage"),
    ("Port Calls", "/port-calls"),
]


def navbar():
    return dbc.Navbar(
        className="top-navbar",
        color="white",
        dark=False,
        sticky="top",
        children=dbc.Container(
            fluid=True,
            className="navbar-inner",
            children=[
                dcc.Link(
                    className="brand-link",
                    href="/",
                    children=[
                        html.Div(className="brand-mark", children="PV"),
                        html.Div(
                            children=[
                                html.Div("PORT VESSEL", className="brand-title"),
                                html.Div(
                                    "USLAX Operations Intelligence",
                                    className="brand-subtitle",
                                ),
                            ]
                        ),
                    ],
                ),
                dbc.Nav(
                    className="nav-links",
                    navbar=True,
                    children=[
                        dbc.NavItem(
                            dcc.Link(
                                label,
                                href=path,
                                id=f"nav-link-{label.lower().replace(' ', '-')}",
                                className="nav-link-custom",
                            )
                        )
                        for label, path in NAV_ITEMS
                    ],
                ),
                html.Div(
                    className="navbar-meta",
                    children=[
                        html.Span("AIS-derived analytics", className="status-pill"),
                        html.Span("USLAX", className="port-pill"),
                    ],
                ),
            ],
        ),
    )


def page_header(title, eyebrow, description):
    return html.Section(
        className="page-header",
        children=[
            html.Div(className="eyebrow", children=eyebrow),
            html.H1(title, className="page-title"),
            html.P(description, className="page-description"),
            dbc.Alert(
                [
                    html.I(className="bi bi-info-circle-fill me-2"),
                    html.Span(DATA_SCOPE_TEXT),
                ],
                className="scope-alert",
                color="light",
            ),
        ],
    )


def kpi_card(title, value, subtitle, icon, accent="navy", tooltip=None):
    tooltip_id = (
        f"tooltip-{title.lower().replace(' ', '-').replace('(', '').replace(')', '')}"
    )

    return dbc.Card(
        className=f"kpi-card kpi-{accent}",
        children=dbc.CardBody(
            [
                html.Div(
                    className="kpi-topline",
                    children=[
                        html.Div(
                            [
                                html.Div(title, id=tooltip_id, className="kpi-label"),
                                dbc.Tooltip(
                                    tooltip or subtitle,
                                    target=tooltip_id,
                                    placement="top",
                                ),
                            ]
                        ),
                        html.Div(
                            className="kpi-icon",
                            children=html.I(className=f"bi {icon}"),
                        ),
                    ],
                ),
                html.Div(value, className="kpi-value"),
                html.Div(subtitle, className="kpi-subtitle"),
            ]
        ),
    )


def section_card(title, subtitle=None, children=None, class_name=""):
    return dbc.Card(
        className=f"section-card {class_name}",
        children=[
            dbc.CardHeader(
                className="section-card-header",
                children=[
                    html.Div(title, className="section-card-title"),
                    (
                        html.Div(subtitle, className="section-card-subtitle")
                        if subtitle
                        else None
                    ),
                ],
            ),
            dbc.CardBody(children or [], className="section-card-body"),
        ],
    )


def empty_state(title, detail):
    return html.Div(
        className="empty-state",
        children=[
            html.Div(html.I(className="bi bi-inbox"), className="empty-icon"),
            html.H5(title),
            html.P(detail),
        ],
    )


def footer():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return html.Footer(
        className="app-footer",
        children=dbc.Container(
            fluid=True,
            children=[
                html.Span("Confidential – Internal Analytics Use"),
                html.Span(f"Last application refresh: {timestamp}"),
            ],
        ),
    )