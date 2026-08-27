import os
from datetime import datetime, timezone

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, callback, dcc, html

from components.layout import footer, navbar


app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Port Vessel | USLAX Operations",
    suppress_callback_exceptions=True,
)

server = app.server


app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="app-session-store", storage_type="session"),
        dcc.Store(
            id="app-last-refreshed-store",
            data=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            storage_type="memory",
        ),
        navbar(),
        html.Main(
            className="main-content",
            children=[dash.page_container],
        ),
        footer(),
    ],
)


@callback(
    Output("nav-link-overview", "className"),
    Output("nav-link-anchorage", "className"),
    Output("nav-link-port-calls", "className"),
    Input("url", "pathname"),
)
def highlight_active_nav(pathname):
    pathname = (pathname or "/").rstrip("/") or "/"

    overview_class = "nav-link-custom"
    anchorage_class = "nav-link-custom"
    port_calls_class = "nav-link-custom"

    if pathname == "/anchorage":
        anchorage_class = "nav-link-custom nav-link-active"
    elif pathname == "/port-calls":
        port_calls_class = "nav-link-custom nav-link-active"
    else:
        overview_class = "nav-link-custom nav-link-active"

    return overview_class, anchorage_class, port_calls_class


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )