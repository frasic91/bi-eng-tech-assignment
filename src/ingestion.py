#IMPORT
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, when, current_date, datediff


spark = SparkSession.builder.getOrCreate()

# CONFIGURATION

TABLEAU_SERVER_URL = "https://your-tableau-server.com"
TABLEAU_API_VERSION = "3.21"
TABLEAU_USERNAME = "your_user"
TABLEAU_PASSWORD = "your_password"
TABLEAU_SITE_NAME = ""

# AUTHENTICATION

def get_tableau_session():
    url = f"{TABLEAU_SERVER_URL}/api/{TABLEAU_API_VERSION}/auth/signin"

    payload = {
        "credentials": {
            "name": TABLEAU_USERNAME,
            "password": TABLEAU_PASSWORD,
            "site": {"contentUrl": TABLEAU_SITE_NAME}
        }
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()

    data = res.json()
    token = data["credentials"]["token"]
    site_id = data["credentials"]["site"]["id"]

    return token, site_id


# FETCH DASHBOARDS

def fetch_dashboards(token, site_id):
    url = f"{TABLEAU_SERVER_URL}/api/{TABLEAU_API_VERSION}/sites/{site_id}/views"

    headers = {
        "X-Tableau-Auth": token,
        "Accept": "application/json"
    }

    all_views = []
    page_number = 1
    page_size = 100

    while True:
        params = {"pageSize": page_size, "pageNumber": page_number}
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()

        data = res.json()
        views = data.get("views", {}).get("view", [])

        if not views:
            break

        all_views.extend(views)

        total = int(data["pagination"]["totalAvailable"])
        if len(all_views) >= total:
            break

        page_number += 1

    return all_views

# MEDALLION ARCHITECTURE
# BRONZE LAYER

def load_bronze(data):
    df = spark.createDataFrame(data)

    df = df.withColumn("ingestion_timestamp", current_timestamp())

    df.write.format("delta") \
        .mode("overwrite") \
        .saveAsTable("bi_metadata.bronze_dashboards")


# SILVER LAYER

def transform_silver():
    df = spark.table("bi_metadata.bronze_dashboards")

    silver_df = df.select(
        col("id").alias("asset_id"),
        col("name").alias("asset_name"),
        col("contentUrl").alias("content_url"),
        col("workbook.id").alias("workbook_id"),
        col("owner.id").alias("owner_id"),
        col("createdAt").alias("created_at"),
        col("updatedAt").alias("last_updated"),
        col("ingestion_timestamp")
    )

    silver_df = silver_df.withColumn(
        "status",
        when(datediff(current_date(), col("last_updated")) > 90, "stale")
        .when(col("last_updated").isNotNull(), "active")
        .otherwise("unknown")
    )

    silver_df = silver_df.withColumn(
        "last_synced_at",
        current_timestamp()
    )

    return silver_df


# MERGE

def upsert_silver(silver_df):
    silver_df.createOrReplaceTempView("updates")

    spark.sql("""
        CREATE TABLE IF NOT EXISTS bi_metadata.dashboards (
            asset_id STRING,
            asset_name STRING,
            content_url STRING,
            workbook_id STRING,
            owner_id STRING,
            created_at STRING,
            last_updated STRING,
            ingestion_timestamp TIMESTAMP,
            status STRING,
            last_synced_at TIMESTAMP
        ) USING DELTA
    """)

    spark.sql("""
        MERGE INTO bi_metadata.dashboards t
        USING updates s
        ON t.asset_id = s.asset_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)


# LOG OUT

def sign_out(token):
    url = f"{TABLEAU_SERVER_URL}/api/{TABLEAU_API_VERSION}/auth/signout"
    headers = {"X-Tableau-Auth": token}
    requests.post(url, headers=headers)

# MAIN

def main():
    token = None

    try:
        token, site_id = get_tableau_session()
        data = fetch_dashboards(token, site_id)

        load_bronze(data)

        silver_df = transform_silver()
        upsert_silver(silver_df)

        print(f"Pipeline completed: {len(data)} dashboards processed")

    except Exception as e:
        print(f"Error: {e}")
        raise

    finally:
        if token:
            sign_out(token)

if __name__ == "__main__":
    main()
