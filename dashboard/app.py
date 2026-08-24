from pathlib import Path
import duckdb
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

DB_PATH = "data/warehouse/portvessel.duckdb"
CONGESTION = "data/processed/ais_scope/agg_port_congestion_daily_2024-12-27_2024-12-29.parquet"
DWELL = "data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"

app = Dash(__name__)


def query(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


congestion = query(f"SELECT * FROM read_parquet('{CONGESTION}') ORDER BY metric_date")
dwell = query(f"""
    SELECT
        anchorage_name,
        MEDIAN(observed_dwell_minutes) FILTER (WHERE eligible_for_persistent_metrics) AS median_minutes,
        COUNT(*) FILTER (WHERE eligible_for_persistent_metrics) AS episodes
    FROM read_parquet('{DWELL}')
    GROUP BY anchorage_name
    HAVING episodes > 0
    ORDER BY episodes DESC
""")

app.layout = html.Div([
    html.H1("PortVessel Local Dashboard"),
    html.P("Observed AIS-derived metrics; not guaranteed operational truth."),
    dcc.Graph(
        figure=px.line(
            congestion,
            x="metric_date",
            y="observed_port_calls",
            markers=True,
            title="Observed Port Calls by Date",
        )
    ),
    dcc.Graph(
        figure=px.bar(
            dwell,
            x="anchorage_name",
            y="median_minutes",
            hover_data=["episodes"],
            title="Median Persistent Observed Anchorage Dwell",
        )
    ),
])

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)