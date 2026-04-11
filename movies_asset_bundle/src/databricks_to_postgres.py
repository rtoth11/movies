import argparse
import datetime
import json
import logging
import os

import boto3
from pyspark.dbutils import DBUtils
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    IntegerType, LongType, ShortType, DoubleType, FloatType, DecimalType,
    StringType, BooleanType, TimestampType, DateType, BinaryType
)

AWS_ACCESS_KEY_SECRET = "aws_access_key_id"
AWS_SECRET_KEY_SECRET = "aws_secret_access_key"

TEMPORARY_CSVS_VOLUME_PATH = "/Volumes/main/default/csvs_temp_volume"
TEMPORARY_CSVS_VOLUME = "main.default.csvs_temp_volume"
S3_PREFIX = "databricks_exports"


def get_spark() -> SparkSession:
    try:
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.getOrCreate()
    except ImportError:
        return SparkSession.builder.getOrCreate()


def get_secret(secret_name, secret_scope, db_utils):
    try:
        return db_utils.secrets.get(scope=secret_scope, key=secret_name)
    except Exception as e:
        raise RuntimeError(
            f"Failed to read secret '{secret_name}' from scope '{secret_scope}': {e}."
        )


def spark_type_to_postgres(spark_type):
    if isinstance(spark_type, (IntegerType, ShortType)):
        return "INTEGER"
    if isinstance(spark_type, LongType):
        return "BIGINT"
    if isinstance(spark_type, (FloatType, DoubleType)):
        return "DOUBLE PRECISION"
    if isinstance(spark_type, DecimalType):
        precision = spark_type.precision if getattr(spark_type, "precision", None) is not None \
            else 38
        scale = spark_type.scale if getattr(spark_type, "scale", None) is not None else 10
        return f"NUMERIC({precision},{scale})"
    if isinstance(spark_type, (StringType, BinaryType)):
        return "TEXT"
    if isinstance(spark_type, BooleanType):
        return "BOOLEAN"
    if isinstance(spark_type, TimestampType):
        return "TIMESTAMP"
    if isinstance(spark_type, DateType):
        return "DATE"
    return "TEXT"


def spark_schema_to_columns(spark_schema):
    """Convert a Spark StructType to the column list the Lambda expects."""
    return [
        {
            "name": field.name,
            "type": spark_type_to_postgres(field.dataType),
            "nullable": field.nullable,
        }
        for field in spark_schema.fields
    ]


def export_table_to_csvs(catalog, schema, table):
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {TEMPORARY_CSVS_VOLUME}")

    df = spark.table(f"{catalog}.{schema}.{table}")
    df = df.filter(df["inserted_at"] > datetime.datetime.now() - datetime.timedelta(hours=1))
    csvs_path = os.path.join(TEMPORARY_CSVS_VOLUME_PATH, f"{table}_csv")

    if len(df.head(1)) == 0:
        return None, None

    logging.debug(f"Writing CSV to {csvs_path}.")
    df.write \
        .format("csv") \
        .option("header", "true") \
        .option("quote", "\"") \
        .option("escape", "\"") \
        .mode("overwrite") \
        .save(csvs_path)

    return csvs_path, df.schema


def delete_s3_files(s3_client, s3_bucket, prefix):
    logging.debug(f"Deleting existing S3 files under prefix '{prefix}/'.")
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_bucket, Prefix=f"{prefix}/")

    objects_to_delete = []
    for page in pages:
        for obj in page.get("Contents", []):
            objects_to_delete.append({"Key": obj["Key"]})

    if objects_to_delete:
        # Split list into chunks of 1000 (S3 delete_objects limit)
        delete_chunks = [objects_to_delete[i:i + 1000]
                         for i in range(0, len(objects_to_delete), 1000)]
        for chunk in delete_chunks:
            s3_client.delete_objects(Bucket=s3_bucket, Delete={"Objects": chunk})
        logging.debug(f"Deleted {len(objects_to_delete)} objects from S3.")
    else:
        logging.debug("No existing S3 files to delete.")


def empty_volume(volume_path):
    if os.path.exists(volume_path):
        for file_name in os.listdir(volume_path):
            file_path = os.path.join(volume_path, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                for sub_file in os.listdir(file_path):
                    os.remove(os.path.join(file_path, sub_file))
                os.rmdir(file_path)


def invoke_pg_import_lambda(lambda_name, target_schema, s3_bucket, region, table_specs):
    """
    Call the pg-import Lambda with the full list of tables to import.
    Each entry in table_specs is {"table": str, "s3_keys": [...], "columns": [...]}.
    The Lambda runs inside the VPC and handles all PG interaction.
    """
    payload = {
        "target_schema": target_schema,
        "s3_bucket": s3_bucket,
        "region": region,
        "tables": table_specs,
        "refresh_materialized_view": True,
    }

    logging.info(f"Invoking Lambda '{lambda_name}' for {len(table_specs)} table(s).")
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType="RequestResponse",   # synchronous — wait for completion
        Payload=json.dumps(payload).encode(),
    )

    status_code = response["StatusCode"]
    response_payload = json.loads(response["Payload"].read())

    if status_code != 200 or response_payload.get("FunctionError"):
        raise RuntimeError(
            f"Lambda invocation failed (HTTP {status_code}): {response_payload}."
        )

    logging.info(f"Lambda response: {response_payload}.")
    return response_payload


def export_schema_to_postgres(source_catalog,
                              source_schema,
                              target_schema,
                              s3_bucket,
                              s3_prefix,
                              lambda_name,
                              region):
    prefix = s3_prefix.strip("/")

    tables = [
        t.name for t in spark.catalog.listTables(f"{source_catalog}.{source_schema}")
        if t.tableType in ("MANAGED", "VIEW", "EXTERNAL", "TABLE")
    ]
    if not tables:
        logging.warning(f"No tables found in schema '{source_catalog}.{source_schema}'.")
        return

    logging.debug(f"Found tables: {tables}.")

    empty_volume(TEMPORARY_CSVS_VOLUME_PATH)
    delete_s3_files(s3, s3_bucket, prefix)

    table_specs = []

    for table in tables:
        logging.info(f"Processing table: {table}.")

        local_path_to_csvs, spark_schema = export_table_to_csvs(
            source_catalog, source_schema, table)

        if local_path_to_csvs is None:
            logging.info(f"No new data for table '{table}', skipping.")
            continue

        s3_keys = []
        for file_name in os.listdir(local_path_to_csvs):
            if not file_name.endswith(".csv"):
                continue
            local_file_path = os.path.join(local_path_to_csvs, file_name)
            s3_key = f"{prefix}/{table}/{file_name}"
            logging.debug(f"Uploading {local_file_path} to s3://{s3_bucket}/{s3_key}.")
            s3.upload_file(local_file_path, s3_bucket, s3_key)
            s3_keys.append(s3_key)

        for file_name in os.listdir(local_path_to_csvs):
            os.remove(os.path.join(local_path_to_csvs, file_name))
        os.rmdir(local_path_to_csvs)

        table_specs.append({
            "table": table,
            "s3_keys": s3_keys,
            "columns": spark_schema_to_columns(spark_schema),
        })
        logging.info(f"Uploaded {len(s3_keys)} CSV(s) for table '{table}'.")

    if table_specs:
        # Single Lambda call for all tables — the Lambda refreshes the
        # materialized view once after all imports complete.
        invoke_pg_import_lambda(
            lambda_name=lambda_name,
            target_schema=target_schema,
            s3_bucket=s3_bucket,
            region=region,
            table_specs=table_specs,
        )
    else:
        logging.info("No new data was found; skipping Lambda invocation.")

    delete_s3_files(s3, s3_bucket, prefix)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-catalog", required=True)
    parser.add_argument("--source-schema", required=True)
    parser.add_argument("--secret-scope", required=True)
    parser.add_argument("--s3-bucket-name", required=True)
    parser.add_argument("--lambda-name", required=True,
                        help="Name of the pg-import Lambda function")
    parser.add_argument("--aws-region", default="us-east-1")
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
    lambda_client = boto3.client("lambda", **boto3_kwargs, region_name=args.aws_region)

    export_schema_to_postgres(
        source_catalog=args.source_catalog,
        source_schema=args.source_schema,
        target_schema=args.source_schema,
        s3_bucket=args.s3_bucket_name,
        s3_prefix=S3_PREFIX,
        lambda_name=args.lambda_name,
        region=args.aws_region,
    )

    logging.info("All done.")
