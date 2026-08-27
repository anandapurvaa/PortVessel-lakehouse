param(
    [string]$ProjectId = "cloudprojects-506123",
    [string]$Region = "europe-west3",
    [string]$Repository = "portvessel",
    [string]$ImageName = "quality",
    [string]$Tag = "v5"
)

$ErrorActionPreference = "Stop"

$image = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$Tag"

$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $ProjectId) {
    gcloud config set project $ProjectId
}

gcloud builds submit `
  --project=$ProjectId `
  --region=$Region `
  --tag=$image `
  .

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Build failed"
}

Write-Host "Built and pushed: $image"
Write-Host "Set this in dev.tfvars:"
Write-Host "quality_image = `"$image`""
