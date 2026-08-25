param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$SourceDate,

    [string]$ProjectId = "cloudprojects-506123",
    [string]$Region = "europe-west3",
    [string]$JobName = "portvessel-batch-dev",
    [string]$DbtDir = ".\dbt",
    [string]$GoldDataset = "portvessel_dev_gold"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$File,
        [string[]]$Arguments
    )

    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $File $($Arguments -join ' ')"
    }
}

$ProcBucket = (& terraform -chdir=infra/environments/dev output -raw processed_bucket).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ProcBucket)) {
    throw "Could not retrieve the processed GCS bucket from Terraform."
}

$runStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$runPrefix = "daily-$SourceDate-$runStamp"

$loads = @(
    @{ SourceObject = "gold/fct_anchorage_dwell/run_date=$SourceDate/fct_anchorage_dwell.parquet"; Table = "fct_anchorage_dwell" },
    @{ SourceObject = "gold/fct_port_call/run_date=$SourceDate/fct_port_call.parquet"; Table = "fct_port_call" },
    @{ SourceObject = "gold/agg_port_congestion_daily/run_date=$SourceDate/agg_port_congestion_daily.parquet"; Table = "agg_port_congestion_daily" },
    @{ SourceObject = "gold/vessel_operational_risk_flags/run_date=$SourceDate/vessel_operational_risk_flags.parquet"; Table = "vessel_operational_risk_flags" }
)

foreach ($load in $loads) {
    $objectUri = "gs://$ProcBucket/$($load.SourceObject)"
    & gcloud storage objects describe $objectUri --project=$ProjectId *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Missing source object: $objectUri"
    }

    $envVars = @(
        "GCP_PROJECT_ID=$ProjectId"
        "GCS_SOURCE_BUCKET=$ProcBucket"
        "SOURCE_OBJECT=$($load.SourceObject)"
        "BQ_DATASET=$GoldDataset"
        "BQ_TABLE=$($load.Table)"
        "SOURCE_DATE=$SourceDate"
        "RUN_ID=$runPrefix-$($load.Table)"
        "BQ_LOCATION=$Region"
        "AUDIT_DATASET=portvessel_dev_staging"
        "AUDIT_TABLE=ingestion_run_audit"
        "PORTVESSEL_ENV=dev"
    ) -join ","

    Invoke-Checked "gcloud" @(
        "run", "jobs", "update", $JobName,
        "--update-env-vars=$envVars",
        "--region=$Region",
        "--project=$ProjectId"
    )

    Invoke-Checked "gcloud" @(
        "run", "jobs", "execute", $JobName,
        "--region=$Region",
        "--wait",
        "--project=$ProjectId"
    )
}

Push-Location $DbtDir
try {
    $env:DBT_PROFILES_DIR = (Get-Location).Path
    Invoke-Checked "dbt" @("source", "freshness")
    Invoke-Checked "dbt" @("build", "--select", "marts")
}
finally {
    Pop-Location
}

Write-Host "Daily pipeline completed successfully for $SourceDate"
