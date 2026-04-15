import argparse
import datetime
import os

import boto3
from pyspark.dbutils import DBUtils

from databricks_to_postgres import (
    get_spark,
    get_secret,
    delete_s3_files,
    AWS_SECRET_KEY_SECRET,
    AWS_ACCESS_KEY_SECRET
)


def copy_s3_to_volume(s3_client, bucket_name: str, s3_prefix: str, local_volume_path: str) -> None:
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            s3_key = obj["Key"]
            # Preserve relative path structure under the volume
            relative_path = os.path.relpath(s3_key, s3_prefix)
            local_path = os.path.join(local_volume_path, relative_path)

            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3_client.download_file(bucket_name, s3_key, local_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--s3-bucket-name", required=True)
    parser.add_argument("--pg-export-s3-path", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--bronze-schema-name", required=True)
    parser.add_argument("--asset-bundle-target", required=True)
    parser.add_argument("--secret-scope", required=True)
    args = parser.parse_args()

    spark = get_spark()
    dbutils = DBUtils(spark)

    aws_access_key = get_secret(AWS_ACCESS_KEY_SECRET, args.secret_scope, dbutils)
    aws_secret_key = get_secret(AWS_SECRET_KEY_SECRET, args.secret_scope, dbutils)

    boto3_kwargs = {
        "aws_access_key_id": aws_access_key,
        "aws_secret_access_key": aws_secret_key,
    }
    s3 = boto3.client("s3", **boto3_kwargs)

    spark.sql("CREATE SCHEMA IF NOT EXISTS movies.processed_searches")
    spark.sql("CREATE VOLUME IF NOT EXISTS movies.processed_searches.archive")

    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_volume_path = f"/Volumes/movies/processed_searches/archive/{current_time}"
    os.makedirs(staging_volume_path, exist_ok=True)

    copy_s3_to_volume(s3, args.s3_bucket_name, args.pg_export_s3_path, staging_volume_path)

    df = spark.read.option("multiline","true").json(staging_volume_path)

    if len(df.head(1)) == 0:
        print("No data to import. Exiting.")
        exit(0)

    if not spark.catalog.tableExists(f"{args.catalog}.{args.bronze_schema_name}.bronze_searches"):
        df.limit(0).write.format("delta").saveAsTable(
            f"{args.catalog}.{args.bronze_schema_name}.bronze_searches")
    df.createOrReplaceTempView(f"{args.catalog}.{args.bronze_schema_name}.new_searches")
    spark.sql(f"""
        MERGE INTO {args.catalog}.{args.bronze_schema_name}.bronze_searches t
        USING new_searches s ON t.search_id = s.search_id
        WHEN NOT MATCHED THEN INSERT *
    """)

    if args.asset_bundle_target != "prod":
        dbutils.fs.rm(staging_volume_path, recurse=True)

    delete_s3_files(s3, args.s3_bucket_name, prefix=args.pg_export_s3_path)

    print("Data successfully imported.")
