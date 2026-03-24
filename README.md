# bi-eng-tech-assignment

# Overview
This project implements a pipeline to ingest and transform BI data from Tableau dashboards, the solution uses Python for data ingestion and Databricks (PySpark + Delta Lake) for data processing and storage.
Data are extracted using the Tableau REST API via a Python script that handles authentication, data extraction, transformation, and loading.

# Part 1 - Architecture
- The pipeline follows medallion architecture with a bronze layer (raw metadata are ingested from API and stored in a Delta table) and a silver layer (cleaned and structured dataset with renamed and new fields) and it is structured as follow:
  1.  Authenticate with Tableau API
  2.  Fetch dashboards metadata
  3.  Store raw data in Bronze table
  4.  Transform data into Silver layer
  5.  Update into final Delta table using MERGE
- The pipeline can be  scheduled and refreshed with a specific frequency (daily is recomended).
- There aren't sensitive information stored in production and credentials could be stored safely in Databricks Secrets or environment variables. 
- There are these precautions to manage failures: raise_for_status() in the API call, try/except logic in the pipeline, job logs that indicates errors.
- Data are stored using Delta Lake with MERGE for data updates, the tables created are: bi_metadata.bronze_dashboards (for raw data) and bi_metadata.dashboards (for the clean dataset). The MERGE action on a PK ensures also the idempotency.
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
I chose Databricks with Delta Lake to support scalability, incremental processing, and future extensibility (and also beacuse I well know the the platform).

The medallion architecture ensures clear separation between raw and processed data, improving maintainability and reusability.
It is possible also to use the silver table for a gold structure. 

# Part 2 - Data Governance
- To ensure consistency above all dashboard a Business centralized metric definition is needed (e.g. define metrics in a semantic layer and use them in all dashboards).
- In order to reduce inconsistencies and improving data reliability a single source of truth is needed, that means all the dashboards use the same sources.
- Metadata and Lineage tracking help to understand which data sources and transformations feed each dashboard, enabling easier debugging and impact analysis.
- The detection of outdated or incorrect data sources is foundamental to identify connections to deprecated or outdated datasets and flag them for review, and it is enabled by monitoring dashboard metadata.
- Standardization and naming conventions for metrics, tables, and dashboards is mandatory to avoid confusion and duplication.
- A Governance process for metric definitions with review processes that involve stakeholders is foundamental to validate and approve new or updated metrics.
- Maintain clear documentation (e.g. data catalog, table and column comments especially in gold structures) in order to enable the user to easily understand and trust the metrics used in dashboards.
- If multiple teams define the same metric differently, the best way to solve this problem is to involve all the stakeholders and make sure they agree on a single, definitive version of the metric. 


# Part 3 - Dashboard Design Thinking
To monitor BI health and usage, I would be included the following metrics:

1. Active dashboards (%) in the last 60 days --> The KPI measures the % of dashboards used at least once in the last 60 days.
2. Outdated dashboards in the last 180 days --> The KPI combined the number of dashboards unused in the last 180 days and the relevant list, these are the dashboards that could be put on a decommissioning list.
3. Top Dashboards by Usage --> Top 10 most used dashboards, these are the most important dashboards for business and those for which maintenance will be a priority.
4. Failed Refresh Count --> The KPI measures the number of dashboard with failed refresh, it helps to measures data reliability and to identifies pipeline issues. It could be helpful also the detailed list of failes refresh dashboards.
5. Usage by Owner or Team --> Aggregate usage by owner or team, in order to identify the top and worse users or groups.
6. Unique Users (per dashboard) --> The KPI count the number of unique users for a dashboard in order to measure the dashboard adoption.


