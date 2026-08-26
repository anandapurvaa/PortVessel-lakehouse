$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Contract = "contracts/reference_geometry_contract.json"
$Zones = "data/reference/normalized/reference_features.ndjson"
$Database = "data/local/portvessel.duckdb"
$InitSql = "scripts/local_spatial_init.sql"
$EnrichmentSql = "sql/duckdb_spatial_enrichment.sql"
$SessionSql = "sql/sessionize_vessel_states.sql"

foreach ($path in @($Contract, $Zones, $InitSql, $EnrichmentSql, $SessionSql)) {
    if (-not (Test-Path $path)) {
        throw "Required file not found: $path"
    }
}

if (-not (Test-Path "data/fixtures/ais_2024-01-04_sample.parquet")) {
    throw "Required AIS fixture not found: data/fixtures/ais_2024-01-04_sample.parquet"
}

python tools/validate_geometry.py $Contract $Zones

& duckdb $Database `
    -init $InitSql `
    -c ".read $EnrichmentSql" `
    -c ".read $SessionSql"

if ($LASTEXITCODE -ne 0) {
    throw "DuckDB pipeline failed with exit code $LASTEXITCODE"
}

python -c "import duckdb; c=duckdb.connect('data/local/portvessel.duckdb'); print(c.sql('SELECT vessel_state, COUNT(*) AS sessions FROM vessel_state_sessions GROUP BY vessel_state ORDER BY vessel_state'))"
