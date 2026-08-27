param(
    [Parameter(Mandatory=$true)]
    [string]$ProcessDate,
    [Parameter(Mandatory=$true)]
    [string]$RawBucket = "cloudprojects-506123-portvessel-dev-raw",
    [string]$ProjectId = "cloudprojects-506123",
    [string]$Dataset = "portvessel_dev_staging",
    [string]$Table = "ais_pings"
)

$ErrorActionPreference = "Stop"
$location = "europe-west3"
$uri = "gs://$RawBucket/raw/ais/observed_date=$ProcessDate/ais_$ProcessDate`_sample.parquet"
$target = "$ProjectId`:$Dataset.$Table"

bq --location=$location load `
  --project_id=$ProjectId `
  --source_format=PARQUET `
  --replace `
  $target `
  $uri

if ($LASTEXITCODE -ne 0) {
    throw "BigQuery load failed with exit code $LASTEXITCODE"
}

bq --location=$location query `
  --use_legacy_sql=false `
  "SELECT COUNT(*) AS rows, COUNT(DISTINCT mmsi) AS vessels, MIN(observed_at_utc) AS first_observation, MAX(observed_at_utc) AS last_observation FROM \\`$target\\`;"
