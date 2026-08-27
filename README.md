# PortVessel Lakehouse

A production-style maritime geospatial data platform that converts public AIS vessel-position telemetry into quality-aware Port of Los Angeles (USLAX) operational analytics.

The project ingests daily AIS source data, preserves immutable raw files, validates and loads vessel pings, applies geofences, reconstructs vessel states, sessionizes port calls, produces Gold-layer congestion marts, and serves the results through a deployed Plotly Dash dashboard (https://portvessel-dashboard-dev-20298064017.europe-west3.run.app).

> **Data scope:** The current dashboard covers USLAX geofenced AIS observations from January 2024 onward. Port-duration metrics use only fully observed calls. Anchorage and berth-proximity metrics use fully observed intervals for the relevant metric.
>
> **Important:** This project is an operational analytics demonstration. It does not provide guaranteed ETAs, legal berth-call records, demurrage calculations, or complete visibility of every vessel.

---

## Table of contents

- [Business problem](#business-problem)
- [What the platform delivers](#what-the-platform-delivers)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Data source and scope](#data-source-and-scope)
- [Data pipeline](#data-pipeline)
- [Data quality and observability](#data-quality-and-observability)
- [Analytics model](#analytics-model)
- [Dashboard](#dashboard)
- [Repository structure](#repository-structure)
- [Run locally](#run-locally)
- [Run the cloud pipeline](#run-the-cloud-pipeline)
- [Deploy the dashboard](#deploy-the-dashboard)
- [Validation queries](#validation-queries)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)

---

## Business problem

Port congestion creates downstream uncertainty for terminals, freight forwarders, drayage operations, and supply-chain control towers. Raw AIS data contains position reports, but it does not directly answer operational questions such as:

- Which vessels are waiting at anchorage?
- How long do observed vessel port calls last?
- How long are vessels observed near berth geofences?
- Which observations are sufficiently complete to support duration-based KPIs?
- How many detected calls are incomplete because the available data begins or ends during a call?

PortVessel Lakehouse addresses this gap by turning raw vessel telemetry into auditable, quality-aware operational facts.

## What the platform delivers

The current USLAX implementation produces:

- Daily detected vessel port-call counts.
- Distinct vessel counts.
- Complete, fully observed port-call counts.
- Port-duration median, mean, and P90 metrics.
- Anchorage dwell facts and short-dwell distribution views.
- Longest observed anchorage dwell intervals.
- Berth-proximity dwell metrics derived from berth geofences.
- Call-level quality statuses: `observed`, `partial`, `left_censored`, `right_censored`, `both_censored`, and `invalid`.
- A public-facing Plotly Dash dashboard deployed to Cloud Run.

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Source data | NOAA / MarineCadastre AIS data | Public historical vessel position telemetry |
| Ingestion | Python, Docker, Cloud Run Jobs | Date-based source acquisition and raw-file handling |
| Object storage | Google Cloud Storage | Immutable raw and processed lake layers |
| Warehouse | BigQuery and BigQuery GIS | Staging, geospatial enrichment, and analytics storage |
| Transformations | dbt Core | SQL models, tests, lineage, documentation, and marts |
| Orchestration | Google Cloud Workflows | Coordinates ingestion, load, dbt transform, quality, and cursor advancement |
| Scheduling | Cloud Scheduler | Daily Workflow trigger |
| Data quality | dbt tests and quality Cloud Run Job | Validity, completeness, schema, and run-quality checks |
| Infrastructure | Terraform | Repeatable GCP resource provisioning |
| Dashboard | Plotly Dash, dash-bootstrap-components | Portfolio-ready operational analytics UI |
| Deployment | Artifact Registry, Cloud Build, Cloud Run | Dashboard container build and managed hosting |

## Architecture

```text
NOAA / MarineCadastre AIS source
            |
            v
Cloud Run ingestion Job
            |
            v
Google Cloud Storage raw layer
            |
            v
Cloud Run BigQuery loader Job
            |
            v
BigQuery staging tables
            |
            v
Cloud Run dbt transform Job
            |
            v
BigQuery Silver models + BigQuery GIS geofencing
            |
            v
Vessel-state interval reconstruction
            |
            v
Port-call and anchorage-dwell Gold facts
            |
            v
Daily congestion aggregate
            |
            +--------------------------+
            |                          |
            v                          v
Cloud Run quality Job          Plotly Dash on Cloud Run
            |                          |
            v                          v
Audit tables / cursor        Portfolio dashboard URL
```

See [`architecture.md`](architecture.md) for a concise component-level architecture description.

## Data source and scope

### Primary source

The project uses public U.S. Automatic Identification System (AIS) vessel telemetry sourced from NOAA / MarineCadastre data services. AIS reports include vessel identifiers, timestamps, location, speed, navigation data, and selected vessel attributes when present.

The raw source is treated as external telemetry, not ground truth. AIS records can have irregular reporting intervals, duplicates, missing vessel attributes, out-of-order timestamps, and incomplete coverage.

### Initial analytical scope

| Dimension | Current scope |
|---|---|
| Port | Port of Los Angeles (`USLAX`) |
| Geography | Port area, anchorage, and berth-proximity geofences |
| Processing style | Scheduled daily historical batch ingestion |
| Initial period | January 2024 data used for MVP validation and dashboarding |
| Output level | Vessel-state intervals, port calls, anchorage dwells, daily aggregates |
| Out of scope | Global real-time streaming, ML forecasting, legal demurrage, guaranteed ETA predictions |

### Source-data principles

- Original source files are preserved in object storage before transformation.
- Raw records are not silently overwritten.
- Derived observations remain traceable through source metadata and ingestion run IDs.
- AIS completeness is explicitly represented through quality flags and censoring logic.

## Data pipeline

### 1. Workflow orchestration

Google Cloud Workflows orchestrates one source date per execution. A pipeline cursor in BigQuery controls the next date to ingest.

The workflow sequence is:

```text
Read ready cursor
  -> ingestion Job
  -> loader Job
  -> dbt transform Job
  -> quality Job
  -> advance cursor by one day only after success
```

The relevant cursor record is stored in:

```text
portvessel_dev_staging.pipeline_cursor
```

The cursor pattern makes the pipeline restartable and supports controlled historical backfills.

### 2. Ingestion

The ingestion Cloud Run Job receives:

```text
SOURCE_DATE
RUN_ID
```

It acquires the configured source data for one date and writes it to the raw lake layer in Google Cloud Storage. The source date and run ID are propagated through the pipeline to support traceability.

### 3. Load and standardization

The loader Cloud Run Job reads the ingested source asset, validates/loading records, and writes normalized AIS pings into BigQuery staging tables. It also records ingestion audit metadata.

The principal staging tables include:

```text
portvessel_dev_staging.ais_pings
portvessel_dev_staging.ingestion_run_audit
portvessel_dev_staging.pipeline_cursor
```

### 4. dbt transformation layer

The dbt project creates a layered warehouse model:

```text
Staging -> Silver -> Gold
```

- **Staging:** cleaned and deduplicated AIS pings.
- **Silver:** geofenced pings and contiguous vessel-state intervals.
- **Gold:** port-call facts, anchorage dwell facts, and daily congestion metrics.

### 5. Quality checks

The quality stage runs after transformation and before cursor advancement. The workflow advances the cursor only when all pipeline steps succeed.

This prevents the workflow from marking an unfinished date as complete.

## Data quality and observability

### AIS validation

The pipeline handles telemetry uncertainty by applying deterministic validation and quality logic:

- Coordinate validation.
- Timestamp normalization.
- Stable raw-record deduplication using `record_hash`.
- Analytics eligibility flags.
- AIS gap detection.
- Vessel-state splitting after AIS gaps longer than three hours.
- Explicit source-window censoring.
- dbt schema tests and accepted-value tests.

### Censoring and duration quality

A duration can be misleading when the AIS extraction begins or ends while a vessel is already in a geofence. The interval model therefore creates:

```text
is_left_censored
is_right_censored
duration_observability_status
```

Possible statuses:

```text
observed
partial
left_censored
right_censored
both_censored
```

At the port-call level, the model creates:

```text
port_call_quality_status
```

Port-duration metrics are set to `NULL` unless the complete call is fully observed. BigQuery aggregate functions ignore `NULL` values, allowing analytical metrics to exclude incomplete durations without discarding operational records.

### Why this matters

A vessel can have a right-censored port call but still have a fully observed anchorage interval inside that call. Therefore:

- Total port duration uses only complete observed port calls.
- Anchorage dwell metrics use fully observed anchorage intervals.
- Berth-proximity dwell metrics use fully observed berth intervals.
- Detected call counts retain partial and censored records for operational coverage visibility.

## Analytics model

### Silver models

| Model | Grain | Purpose |
|---|---|---|
| `stg_ais_pings` | One normalized AIS ping | Cleans raw source records and applies data-quality flags |
| `int_ais_pings_geofenced` | One eligible ping | Assigns each ping to a prioritized USLAX operational geofence |
| `int_vessel_state_intervals` | One contiguous vessel state interval | Reconstructs vessel state across port area, anchorage, berth, or outside |

### Gold models

| Model | Grain | Purpose |
|---|---|---|
| `fct_port_calls` | One vessel port-call sequence | Calculates observed arrival/departure evidence, state counts, durations, and call quality |
| `fct_anchorage_dwell` | One anchorage state interval | Provides auditable observed anchorage dwell facts and quality statuses |
| `agg_port_congestion_daily` | One port per metric date | Provides daily operational volume, duration, coverage, and quality metrics |

### Key Gold fields

#### `fct_port_calls`

```text
port_call_id
mmsi
imo
vessel_name
port_id
arrival_observed_at_utc
departure_observed_at_utc
port_duration_minutes
anchorage_wait_minutes
berth_dwell_minutes
port_call_quality_status
```

#### `fct_anchorage_dwell`

```text
anchorage_dwell_id
mmsi
imo
vessel_name
zone_id
zone_name
anchorage_entered_at_utc
anchorage_exited_at_utc
anchorage_dwell_minutes
anchorage_dwell_quality_status
```

#### `agg_port_congestion_daily`

```text
metric_date
detected_port_calls
detected_vessels
complete_port_calls
observed_port_calls
partial_calls
left_censored_calls
right_censored_calls
both_censored_calls
port_calls_with_observed_anchorage_wait
port_calls_with_observed_berth_proximity_dwell
median_port_duration_minutes
p90_port_duration_minutes
median_anchorage_wait_minutes
median_berth_proximity_dwell_minutes
```

## Dashboard

The portfolio dashboard is a multi-page Plotly Dash application deployed as a Cloud Run service.

### Overview page

Uses `agg_port_congestion_daily` to provide:

- Total detected port calls.
- Total detected vessels.
- Complete port calls eligible for port-duration metrics.
- Median port duration.
- Detected versus complete daily call trend.
- Port-call observation-quality stacked bars.
- Data-coverage interpretation.

### Anchorage page

Uses `fct_anchorage_dwell` to provide:

- Observed anchorage dwell count.
- Median observed anchorage dwell.
- A short-dwell distribution from 0.0 to 4.0 hours in eight 0.5-hour bands.
- Top five longest fully observed anchorage intervals.
- A sortable, filterable operational detail table.

A dash (`—`) in the table’s dwell column indicates that AIS evidence was insufficient to calculate a valid observed dwell duration.

### Port Calls page

Uses `fct_port_calls` to provide:

- Arrival-date filter.
- Quality-status multi-select filter.
- Default view limited to `observed` port calls.
- Vessel-level arrival, departure, port duration, anchorage wait, berth-proximity dwell, and quality status.
- CSV export.

## Repository structure

```text
PortVessel-lakehouse/
├── app.py                         # Dash application entry point
├── Dockerfile                     # Dashboard Cloud Run image definition
├── requirements.txt               # Dashboard runtime dependencies
├── assets/
│   └── custom.css                 # Dashboard styling
├── components/
│   ├── charts.py                  # Reusable Plotly chart builders
│   └── layout.py                  # Shared navbar, footer, cards, page headers
├── data/
│   └── repository.py              # BigQuery data-access layer
├── pages/
│   ├── overview.py                # Overview dashboard page
│   ├── anchorage.py               # Anchorage dashboard page
│   └── port_calls.py              # Port-call explorer page
├── dbt/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   ├── geospatial/
│   │   └── marts/
│   ├── macros/
│   ├── seeds/
│   └── tests/
├── workflow/
│   └── orchestration_workflow.yaml
├── terraform/
│   └── ...                        # GCP infrastructure resources
├── docs/
│   ├── architecture.md
│   └── runbooks/
└── README.md
```

## Run locally

### Prerequisites

- Python 3.11 or compatible Python runtime.
- Google Cloud SDK authenticated to the deployment project.
- Application Default Credentials for local BigQuery access.
- Access to the project datasets.

### Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dashboard dependencies

```powershell
pip install -r requirements.txt
```

### Authenticate for BigQuery

```powershell
gcloud auth application-default login
```

### Run Dash

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:8050
```

The local app uses the real Gold tables configured in `data/repository.py`:

```text
cloudprojects-506123.portvessel_dev_gold.agg_port_congestion_daily
cloudprojects-506123.portvessel_dev_gold.fct_port_calls
cloudprojects-506123.portvessel_dev_gold.fct_anchorage_dwell
```

## Run the cloud pipeline

### Inspect pipeline cursor

```powershell
bq query --use_legacy_sql=false "
SELECT
  pipeline_name,
  next_source_date,
  status,
  last_run_id,
  updated_at
FROM \`cloudprojects-506123.portvessel_dev_staging.pipeline_cursor\`
WHERE pipeline_name = 'portvessel_noaa_daily_ingestion';
"
```

### Trigger a Workflow execution

The Workflow processes one cursor date at a time.

```powershell
gcloud workflows run WORKFLOW_NAME `
  --location=europe-west3 `
  --project=cloudprojects-506123 `
  --data='{}'
```

Replace `WORKFLOW_NAME` with the deployed Google Cloud Workflow resource name.

### Backfill a date range

For a controlled historical backfill:

1. Pause the Cloud Scheduler job.
2. Set `next_source_date` to the desired initial date.
3. Execute the Workflow sequentially once per date.
4. Verify the cursor advances one day after each successful run.
5. Resume Scheduler after validation.

Example cursor reset:

```powershell
bq query --use_legacy_sql=false "
UPDATE \`cloudprojects-506123.portvessel_dev_staging.pipeline_cursor\`
SET
  next_source_date = DATE '2024-01-01',
  last_run_id = NULL,
  updated_at = CURRENT_TIMESTAMP()
WHERE pipeline_name = 'portvessel_noaa_daily_ingestion'
  AND status = 'ready';
"
```

Do not execute multiple Workflow runs concurrently against the same cursor record.

### Run dbt locally

From the dbt project folder:

```powershell
cd dbt

dbt build --select int_vessel_state_intervals+ --full-refresh
```

This rebuilds the state interval model and downstream Gold facts/marts.

## Deploy the dashboard

The dashboard is packaged as a Docker container, stored in Artifact Registry, and deployed as a Cloud Run service.

### Build image

```powershell
$PROJECT_ID = "cloudprojects-506123"
$REGION = "europe-west3"
$REPOSITORY = "portvessel"
$IMAGE_NAME = "portvessel-dashboard"
$TAG = "v1"
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME`:$TAG"

gcloud builds submit `
  --project=$PROJECT_ID `
  --tag=$IMAGE_URI `
  .
```

### Deploy Cloud Run service

```powershell
$SERVICE_ACCOUNT = "portvessel-dashboard-dev@cloudprojects-506123.iam.gserviceaccount.com"

gcloud run deploy portvessel-dashboard-dev `
  --image=$IMAGE_URI `
  --region=$REGION `
  --project=$PROJECT_ID `
  --service-account=$SERVICE_ACCOUNT `
  --allow-unauthenticated `
  --port=8080 `
  --memory=1Gi `
  --cpu=1 `
  --timeout=120 `
  --max-instances=2 `
  --min-instances=0
```

The service account requires, at minimum:

```text
roles/bigquery.jobUser
roles/bigquery.dataViewer
roles/bigquery.readSessionUser
```

Cloud Run passes the `PORT` environment variable to the container. The dashboard application and Gunicorn entry point must bind to `0.0.0.0:$PORT`.

## Validation queries

### Inspect daily congestion metrics

```powershell
bq query --use_legacy_sql=false "
SELECT
  metric_date,
  detected_port_calls,
  detected_vessels,
  complete_port_calls,
  observed_port_calls,
  partial_calls,
  left_censored_calls,
  right_censored_calls,
  both_censored_calls,
  port_calls_with_observed_anchorage_wait,
  port_calls_with_observed_berth_proximity_dwell,
  median_port_duration_minutes,
  median_anchorage_wait_minutes,
  median_berth_proximity_dwell_minutes
FROM \`cloudprojects-506123.portvessel_dev_gold.agg_port_congestion_daily\`
WHERE port_id = 'USLAX'
ORDER BY metric_date;
"
```

### Inspect port-call quality distribution

```powershell
bq query --use_legacy_sql=false "
SELECT
  port_call_quality_status,
  COUNT(*) AS port_calls,
  COUNTIF(port_duration_minutes IS NOT NULL) AS complete_duration_calls,
  COUNTIF(anchorage_wait_minutes IS NOT NULL) AS observed_anchorage_wait_calls,
  COUNTIF(berth_dwell_minutes IS NOT NULL) AS observed_berth_dwell_calls
FROM \`cloudprojects-506123.portvessel_dev_gold.fct_port_calls\`
WHERE port_id = 'USLAX'
GROUP BY port_call_quality_status
ORDER BY port_call_quality_status;
"
```

### Inspect anchorage dwell quality

```powershell
bq query --use_legacy_sql=false "
SELECT
  anchorage_dwell_quality_status,
  COUNT(*) AS intervals,
  COUNTIF(anchorage_dwell_minutes IS NOT NULL) AS intervals_with_observed_dwell,
  ROUND(AVG(anchorage_dwell_minutes), 1) AS mean_dwell_minutes
FROM \`cloudprojects-506123.portvessel_dev_gold.fct_anchorage_dwell\`
WHERE port_id = 'USLAX'
GROUP BY anchorage_dwell_quality_status
ORDER BY anchorage_dwell_quality_status;
"
```

## Known limitations

- AIS data is an observational telemetry source, not a complete operational system of record.
- Geofence definitions affect port-call and dwell results; boundary versions should be governed in production.
- A vessel state can be split after long AIS reporting gaps, which is intentional to avoid inventing continuous movement or dwell.
- Port-duration figures are available only for fully observed call sequences.
- Berth proximity is inferred from configured berth geofences; it is not proof of an official berth assignment.
- The current scope is one port, one historical period, and scheduled batch processing.
- The dashboard is a portfolio application, not a certified maritime decision system.

## Future improvements

Potential next steps include:

- Multi-port geofence configuration and port comparison views.
- Geofence version/effective-date management.
- Incremental dbt models and partition-aware backfills.
- Dataset freshness SLIs and alerting.
- More detailed terminal and berth reference data.
- Public-safe vessel-data masking for portfolio exposure if licensing or usage requirements require it.
- FastAPI endpoints for selected operational metrics.
- CI/CD checks for dbt tests, container builds, and Terraform plans.
- Data lineage integration and richer run-level observability.
- Additional contextual data such as NOAA PORTS water-level, tide, weather, or terminal reference datasets.

## Portfolio highlights

PortVessel Lakehouse demonstrates:

- Geospatial data engineering with BigQuery GIS.
- Batch orchestration using Google Cloud Workflows and Cloud Run Jobs.
- Cursor-controlled, replayable ingestion.
- Bronze/raw, staging, Silver, and Gold lakehouse modeling.
- dbt SQL transformation, testing, documentation, and lineage practices.
- Explicit data-quality modeling for incomplete observational intervals.
- Containerized deployment through Artifact Registry and Cloud Run.
- An interactive, quality-aware maritime operations dashboard.

## License and attribution

This repository should document the final AIS source terms, attribution requirements, retention rules, and redistribution permissions used by the deployed dashboard. Do not assume public source availability alone grants unrestricted redistribution rights.
