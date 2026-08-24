from pathlib import Path
import duckdb
import plotly.express as px
from dash import Dash, dcc, html

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "portvessel.duckdb"
CONGESTION = ROOT / "data" / "processed" / "ais_scope" / "agg_port_congestion_daily_2024-12-27_2024-12-29.parquet"
DWELL = ROOT / "data" / "processed" / "ais_scope" / "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
FLAGS = ROOT / "data" / "processed" / "ais_scope" / "vessel_operational_risk_flags_2024-12-27_2024-12-29.parquet"

app = Dash(__name__)


def query(sql: str):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


congestion = query(f"SELECT * FROM read_parquet('{CONGESTION.as_posix()}') ORDER BY metric_date")
dwell = query(f"""
    SELECT
        COALESCE(anchorage_name, '[unnamed feature]') AS anchorage_name,
        MEDIAN(observed_dwell_minutes) FILTER (WHERE eligible_for_persistent_metrics) AS median_minutes,
        COUNT(*) FILTER (WHERE eligible_for_persistent_metrics) AS episodes
    FROM read_parquet('{DWELL.as_posix()}')
    GROUP BY 1
    HAVING episodes > 0
    ORDER BY episodes DESC
""")
flags = query(f"""
    SELECT operational_flag, COUNT(*) AS vessels
    FROM read_parquet('{FLAGS.as_posix()}')
    GROUP BY operational_flag
    ORDER BY operational_flag
""")

app.layout = html.Div([
    html.H1("PortVessel Local Dashboard"),
    html.P("Observed AIS-derived metrics; not guaranteed operational truth."),
    html.Div([
        html.H3(f"Observed vessels: {int(congestion['observed_vessels'].sum())}"),
        html.H3(f"Observed port calls: {int(congestion['observed_port_calls'].sum())}"),
    ]),
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
    dcc.Graph(
        figure=px.bar(
            flags,
            x="operational_flag",
            y="vessels",
            title="Observed Vessel Flags",
        )
    ),
])

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
