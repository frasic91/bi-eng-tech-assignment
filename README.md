# bi-eng-tech-assignment

# Overview
This project implements a pipeline to ingest and transform BI data from Tableau dashboards.
The goal is providing visibility of dashboard usage, freshness, and reliability by transforming raw metadata into an analytics dataset.
The solution uses Python for data ingestion and Databricks (PySpark + Delta Lake) for data processing and storage.

# Part 1 - Architecture
- The pipeline follows medallion architecture with a bronze layer (raw metadata ingested from API and stored in a DLT) and a silver layer (cleanded and structured dataset with renamed fields) and it is structured as follow:
  1.  Authenticate with Tableau API
  2.  Fetch dashboards metadata
  3.  Store raw data in Bronze table
  4.  Transform data into Silver layer
  5.  Update into final Delta table using MERGE
- The pipeline can be scheduled as a job in dbt with a specific frequency (daily is reccomended).
- There aren't sensitive information stored in production and credentials could be stored safely in dbt Secrets. 
- There are these precautions to manage failures: raise_for_status() in the API call, try/except logic in the pipeline, job logs that indicates errors.
- Data are stored using Delta Lake with MERGE for data updates, the tables created are: bi_metadata.bronze_dashboards (for raw data) and bi_metadata.dashboards (for the clean dataset). The MERGE action on a PK ensures also the idempotecy.
- Data Transformations (silver layer) is implemented in PySpark and includes: column renaming, Flattening nested fields
and calculated fields (status and last_synced_at).

# Part 1 - Monitoring and Alerting
The dataset allows the monitoring of BI assets:
- Stale dashboards --> Identified via status = 'stale'
- Failed refreshes --> Can be added via additional metadata endpoints
- Usage anomalies --> Based on metrics like views_last_30d

Alerts can be configured via:
- Databricks SQL alerts
- Email / Slack integrations

# Part 1 - Design Decision
I chose Databricks with Delta Lake to support scalability, incremental processing, and future extensibility.

The medallion architecture ensures clear separation between raw and processed data, improving maintainability and reusability.

# Part 2 - Data Governance
- Business centralized metric definition to ensure consistency above all dashboards (e.g. define metrics in a semantic layer and use them in all dashboards).
- Single source of truth, that means all the dashboards use the same sources (gold or silver tables) for the same KPIs in order to reduce inconsistencies and improving data reliability.
- Metadata and Lineage tracking help to understand which data sources and transformations feed each dashboard, enabling easier debugging and impact analysis.
- Detection of outdated or incorrect data sources by monitoring dashboard metadata in order to identify connections to deprecated or outdated datasets and flag them for review.
- Standardization and naming conventions for metrics, tables, and dashboards to avoid confusion and duplication.
- Governance process for metric definitions with review processes that involve stakeholders to validate and approve new or updated metrics.
- Maintain clear documentation (e.g. data catalog, table and column comments especially in gold structures) to in order to enable the user to easily understand and trust the metrics used in dashboards.
- If multiple teams define the same metric differently, the best way to solve this problem is to involve all the stakeholders and make sure they agree on a single, definitive version of the metric. 


# Part 3 - Dashboard Design Thinking
To monitor BI health and usage, I would be included the following metrics:

1. Active dashboards (%) in the last 60 days --> The KPI measures the % of dashboards used at least once in the last 60 days.
2. Outdated dashboards in the last 180 days --> The KPI measures the number of dashboards unused in the last 180 days, 
these are the dashboards that could be put on a decommissioning list.
3. Top Dashboards by Usage --> Top 10 most udes dashboards, these are the most important dashboards for the business and those for which maintenance will be a priority.
4. Failed Refresh Count --> The KPI mesures the number of dashboard with failed refresh, it helps to measures data reliability and to identifies pipeline issues. It could be helpful also the detailed list of failes refresh dashboards
5. Usage by Owner or Team --> Aggregate usage by owner or team, in order to identify the top and worse users or groups
Identifies pipeline issues.
6. Unique Users (per dashboard) --> The KPI count the number of unique users for a dashbord in order to measure the dashboard adoption


