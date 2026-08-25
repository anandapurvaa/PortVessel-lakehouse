param(
    [string]$ProjectId = "cloudprojects-506123",
    [string]$Region = "europe-west3",
    [string]$JobName = "portvessel-batch-dev",
    [string]$DbtDir = ".\dbt",
    [string]$GoldDataset = "portvessel_dev_gold",
    [string]$ProcessedBucket = "",
    [switch]$AllowExistingDate
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

function Get-ProcessedBucket {
    if (-not [string]::IsNullOrWhiteSpace($ProcessedBucket)) {
        return $ProcessedBucket
    }

    $value = (& terraform -chdir=infra/environments/dev output -raw processed_bucket).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        throw "Could not retrieve processed_bucket from Terraform."
    }
    return $value
}

function Get-AvailableRunDates {
    param([string]$Bucket)

    $prefix = "gs://$Bucket/gold/"
    $output = & gcloud storage ls --recursive $prefix --project=$ProjectId 2>$null

    if ($LASTEXITCODE -ne 0) {
        throw "Could not list objects under $prefix"
    }

    $dates = @(
        $output |
        ForEach-Object {
            if ($_ -match 'run_date=(\d{4}-\d{2}-\d{2})/') {
                try {
                    [datetime]::ParseExact(
                        $Matches[1],
                        "yyyy-MM-dd",
                        [Globalization.CultureInfo]::InvariantCulture
                    ).Date
                }
                catch {
                }
            }
        } |
        Where-Object { $_ -ne $null } |
        Sort-Object -Unique
    )

    if ($dates.Count -eq 0) {
        throw "No valid run_date=YYYY-MM-DD objects found in $prefix"
    }

    return $dates
}

function Test-CompleteDate {
    param(
        [string]$Bucket,
        [datetime]$Date
    )

    $dateText = $Date.ToString("yyyy-MM-dd")
    $expected = @(
        "gold/fct_anchorage_dwell/run_date=$dateText/fct_anchorage_dwell.parquet",
        "gold/fct_port_call/run_date=$dateText/fct_port_call.parquet",
        "gold/agg_port_congestion_daily/run_date=$dateText/agg_port_congestion_daily.parquet",
        "gold/vessel_operational_risk_flags/run_date=$dateText/vessel_operational_risk_flags.parquet"
    )

    foreach ($object in $expected) {
        $uri = "gs://$Bucket/$object"
        & gcloud storage objects describe $uri --project=$ProjectId *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
    }

    return $true
}

$bucket = Get-ProcessedBucket
$dates = Get-AvailableRunDates -Bucket $bucket
$completeDates = @(
    $dates |
    Sort-Object -Descending |
    Where-Object { Test-CompleteDate -Bucket $bucket -Date $_ }
)

if ($completeDates.Count -eq 0) {
    throw "No complete date found with all four required gold Parquet files."
}

$sourceDate = $completeDates[0].ToString("yyyy-MM-dd")

if (-not $AllowExistingDate) {
    $auditQuery = @"
SELECT COUNT(*) AS completed_tables
FROM ``$ProjectId.portvessel_dev_staging.ingestion_run_audit``
WHERE source_date = DATE('$sourceDate')
  AND status = 'loaded'
  AND target_dataset = '$GoldDataset'
  AND target_table IN (
    'fct_anchorage_dwell',
    'fct_port_call',
    'agg_port_congestion_daily',
    'vessel_operational_risk_flags'
  )
"@

    $completedTables = (& bq query `
        --project_id=$ProjectId `
        --location=$Region `
        --use_legacy_sql=false `
        --format=csv `
        $auditQuery 2>$null | Select-Object -Last 1).Trim()

    if ($LASTEXITCODE -eq 0 -and $completedTables -eq "4") {
        Write-Host "Newest complete date $sourceDate is already loaded. Nothing to do."
        exit 0
    }
}

$runStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$runPrefix = "daily-$sourceDate-$runStamp"

$loads = @(
    @{ SourceObject = "gold/fct_anchorage_dwell/run_date=$sourceDate/fct_anchorage_dwell.parquet"; Table = "fct_anchorage_dwell" },
    @{ SourceObject = "gold/fct_port_call/run_date=$sourceDate/fct_port_call.parquet"; Table = "fct_port_call" },
    @{ SourceObject = "gold/agg_port_congestion_daily/run_date=$sourceDate/agg_port_congestion_daily.parquet"; Table = "agg_port_congestion_daily" },
    @{ SourceObject = "gold/vessel_operational_risk_flags/run_date=$sourceDate/vessel_operational_risk_flags.parquet"; Table = "vessel_operational_risk_flags" }
)

Write-Host "Selected newest complete source date: $sourceDate"
Write-Host "Processed bucket: $bucket"

foreach ($load in $loads) {
    $envVars = @(
        "GCP_PROJECT_ID=$ProjectId"
        "GCS_SOURCE_BUCKET=$bucket"
        "SOURCE_OBJECT=$($load.SourceObject)"
        "BQ_DATASET=$GoldDataset"
        "BQ_TABLE=$($load.Table)"
        "SOURCE_DATE=$sourceDate"
        "RUN_ID=$runPrefix-$($load.Table)"
        "BQ_LOCATION=$Region"
        "AUDIT_DATASET=portvessel_dev_staging"
        "AUDIT_TABLE=ingestion_run_audit"
        "PORTVESSEL_ENV=dev"
    ) -join ","

    Write-Host "Loading $($load.Table)..."

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

Write-Host "Gold loads completed. Running dbt..."

Push-Location $DbtDir
try {
    $env:DBT_PROFILES_DIR = (Get-Location).Path
    # Source freshness is not used for this finite backfill because
    # fct_port_call has no loaded_at_utc and BigQuery batch freshness
    # is incompatible with the current dbt adapter setup.

    Invoke-Checked "dbt" @("build", "--select", "marts")
}
finally {
    Pop-Location
}

Write-Host "Pipeline completed successfully for $sourceDate"
