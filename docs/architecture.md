# PortVessel Lakehouse Architecture

## Purpose

PortVessel Lakehouse is a scheduled, batch-oriented maritime analytics platform. It transforms public AIS vessel-position telemetry into quality-aware operational metrics for the Port of Los Angeles (`USLAX`).

The design prioritizes replayability, traceability, clear warehouse layers, deterministic geospatial logic, and cost-conscious managed GCP services.

## High-level architecture

```text
                         +--------------------------+
                         | NOAA / MarineCadastre AIS |
                         | historical source data    |
                         +-------------+------------+
                                       |
                                       v
                         +--------------------------+
                         | Cloud Run Job: Ingestion  |
                         | date-based source fetch   |
                         +-------------+------------+
                                       |
                                       v
             +-----------------------------------------------+
             | Google Cloud Storage                           |
             | raw objects / processed assets / replay inputs |
             +-------------------+---------------------------+
                                 |
                                 v
                         +--------------------------+
                         | Cloud Run Job: Loader     |
                         | normalize and load pings  |
                         +-------------+------------+
                                       |
                                       v
             +-----------------------------------------------+
             | BigQuery staging                               |
             | ais_pings / ingestion audits / pipeline cursor |
             +-------------------+---------------------------+
                                 |
                                 v
                         +--------------------------+
                         | Cloud Run Job: dbt Core   |
                         | staging -> Silver -> Gold |
                         +-------------+------------+
                                       |
                                       v
    +-------------------------------------------------------------------+
    | BigQuery analytics warehouse                                      |
    |                                                                   |
    | Silver: stg_ais_pings, int_ais_pings_geofenced, state intervals  |
    | Gold: fct_port_calls, fct_anchorage_dwell, daily congestion      |
    +------------------------------+------------------------------------+
                                   |
                   +---------------+----------------+
                   |                                |
                   v                                v
    +-------------------------------+  +--------------------------------+
    | Cloud Run Job: Quality checks |  | Dash application on Cloud Run  |
    | dbt tests / run validation    |  | charts, filters, CSV export   |
    +---------------+---------------+  +--------------------------------+
                    |                                |
                    v                                v
    +-------------------------------+  +--------------------------------+
    | BigQuery audit + cursor state |  | Browser / portfolio consumers |
    +-------------------------------+  +--------------------------------+
```

## Orchestration

Google Cloud Workflows controls the pipeline. Cloud Scheduler triggers the Workflow on a schedule.

Each Workflow execution processes one source date:

```text
1. Read pipeline_cursor.next_source_date
2. Run ingestion Cloud Run Job
3. Run loader Cloud Run Job
4. Run dbt transformation Cloud Run Job
5. Run data-quality Cloud Run Job
6. Advance the cursor by one day only after all prior stages succeed
```

The cursor is stored in:

```text
portvessel_dev_staging.pipeline_cursor
```

This pattern provides deterministic incremental processing and controlled historical backfills. A failed execution leaves the cursor unchanged, allowing the same date to be retried.

## Storage and warehouse layers

| Layer | Primary technology | Purpose |
|---|---|---|
| Raw / Bronze | Google Cloud Storage | Immutable downloaded source files and replayable ingestion inputs |
| Staging | BigQuery | Loaded normalized source records, pipeline cursor, and ingestion audit data |
| Silver | BigQuery + dbt | Cleaned AIS pings, GIS enrichment, state reconstruction, quality flags |
| Gold | BigQuery + dbt | Port calls, anchorage dwell facts, and daily congestion metrics |
| Serving | Cloud Run + Dash | Interactive portfolio dashboard backed by Gold tables |

## dbt transformation design

### Geofencing

Eligible AIS pings are enriched with operational geofences representing:

```text
port_area
anchorage
berth
outside
```

A prioritized geofence assignment gives each ping one vessel state.

### State reconstruction

`int_vessel_state_intervals` groups consecutive pings by vessel into state intervals. A new interval begins when:

- The vessel state changes.
- The assigned port changes.
- The gap between AIS observations exceeds three hours.
- The vessel has no previous observation.

### Duration observability

Intervals touching the beginning or end of the available source-data window are marked as censored:

```text
observed
partial
left_censored
right_censored
both_censored
```

This prevents the platform from presenting an observed duration as a complete real-world duration when the vessel may already have been in the zone before data started or may remain there after data ends.

### Gold facts

- `fct_port_calls` groups USLAX in-port state intervals into vessel visits. Calls split after more than six hours between observed in-port intervals.
- `fct_anchorage_dwell` exposes anchorage intervals and populates dwell duration only when the interval is fully observed.
- `agg_port_congestion_daily` aggregates detected calls, quality status, complete-call coverage, and valid duration metrics by day.

## Data quality controls

| Control | Purpose |
|---|---|
| Stable record hash | Deduplicates repeated source records |
| Coordinate and timestamp validation | Excludes invalid pings from analytics while preserving raw traceability |
| AIS gap threshold | Stops state intervals from bridging long unobserved periods |
| Censoring flags | Identifies durations truncated by source-window boundaries |
| dbt schema tests | Checks keys, nullability, and accepted status values |
| Quality Job | Validates pipeline-stage outputs before cursor advancement |
| Ingestion audit data | Connects records and Gold outputs to a run identifier |

## Dashboard serving path

The Plotly Dash application is packaged in Docker, stored in Artifact Registry, and deployed to Cloud Run as a web service.

```text
Browser
  -> Cloud Run Dash service
  -> Python repository layer
  -> BigQuery Gold tables
  -> Plotly figures and Dash DataTables
  -> Browser
```

The dashboard includes:

- Overview: detected/complete calls, port-duration metrics, and quality breakdown.
- Anchorage: observed dwell counts, bounded short-dwell distribution, longest dwell events, and interval detail.
- Port Calls: date and quality filtering, vessel-level operational facts, and CSV export.

## Security and access

- Cloud Run Jobs and the Cloud Run dashboard use service accounts rather than local keys.
- The dashboard service account requires BigQuery job creation and read access to the Gold dataset.
- Workflow identity requires permission to run the relevant Cloud Run Jobs and query/update cursor state.
- Terraform manages cloud resources and IAM bindings.
- Public dashboard exposure should be reviewed against source-data terms and any vessel-detail redistribution requirements.

## Operational behavior

### Normal run

```text
Cloud Scheduler -> Workflow -> Jobs -> dbt -> quality -> cursor advance
```

### Failed run

```text
Failed stage -> Workflow fails -> cursor does not advance -> retry same date
```

### Historical backfill

```text
Pause Scheduler
-> reset cursor to desired start date
-> run Workflows sequentially
-> validate staging/Silver/Gold outputs
-> confirm cursor reaches desired next date
-> resume Scheduler
```

## Design decisions

| Decision | Rationale |
|---|---|
| Batch, one date per Workflow run | Suitable for historical AIS MVP and simple replay behavior |
| Cloud Run Jobs instead of always-on workers | Cost-conscious, containerized, and operationally isolated |
| BigQuery GIS for geospatial enrichment | Keeps analytical joins close to warehouse models |
| dbt SQL models for transformations | Testable, documented, lineage-friendly warehouse logic |
| Explicit censoring instead of inferred durations | Prevents overstating AIS observation completeness |
| Gold tables as the dashboard contract | Keeps the UI decoupled from raw telemetry and transformation complexity |
| Cloud Run Dash service | Managed HTTPS hosting with container-based reproducibility |

## Current constraints

- USLAX is the initial configured port.
- AIS is incomplete and may contain irregular reporting intervals.
- Geofence definitions determine state classification and should be versioned for multi-port production use.
- The platform is decision support and analysis, not a legal, financial, navigational, or ETA-prediction system.
