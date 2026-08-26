param(
    [Parameter(Mandatory=$true)]
    [string]$ProcessDate
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python .\tools\daily_process.py --process-date $ProcessDate
if ($LASTEXITCODE -ne 0) {
    throw "Daily processing failed with exit code $LASTEXITCODE"
}
