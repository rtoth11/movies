import argparse
import datetime
import logging
import os

import boto3
import psycopg2
from pyspark.dbutils import DBUtils
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    IntegerType, LongType, ShortType, DoubleType, FloatType, DecimalType,
    StringType, BooleanType, TimestampType, DateType, BinaryType
)

AWS_ACCESS_KEY_SECRET = "aws_access_key_id"
AWS_SECRET_KEY_SECRET = "aws_secret_access_key"

PG_HOST_SECRET = "pg_host"
PG_PORT_SECRET = "pg_port"
PG_DB_SECRET = "pg_database"
PG_USER_SECRET = "pg_user"
PG_PASS_SECRET = "pg_password"

TEMPORARY_CSVS_VOLUME_PATH = "/Volumes/main/default/csvs_temp_volume"
TEMPORARY_CSVS_VOLUME = "main.default.csvs_temp_volume"
S3_PREFIX = "databricks_exports"


def get_spark() -> SparkSession:
    try:
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.getOrCreate()
    except ImportError:
        return SparkSession.builder.getOrCreate()


def get_secret(secret_name):
    try:
        return dbutils.secrets.get(scope=args.secret_scope, key=secret_name)
    except Exception as e:
        raise RuntimeError(f"Failed to read secret '{secret_name}' "
                           f"from scope '{args.secret_scope}': {e}")


def spark_type_to_postgres(spark_type):
    if isinstance(spark_type, (IntegerType, ShortType)):
        return "INTEGER"
    if isinstance(spark_type, LongType):
        return "BIGINT"
    if isinstance(spark_type, (FloatType, DoubleType)):
        return "DOUBLE PRECISION"
    if isinstance(spark_type, DecimalType):
        if hasattr(spark_type, "precision") and spark_type.precision is not None:
            precision = spark_type.precision
        else:
            precision = 38
        if hasattr(spark_type, "scale") and spark_type.scale is not None:
            scale = spark_type.scale
        else:
            scale = 10
        return f"NUMERIC({precision},{scale})"
    if isinstance(spark_type, StringType) or isinstance(spark_type, BinaryType):
        return "TEXT"
    if isinstance(spark_type, BooleanType):
        return "BOOLEAN"
    if isinstance(spark_type, TimestampType):
        return "TIMESTAMP"
    if isinstance(spark_type, DateType):
        return "DATE"
    return "TEXT"


def create_table_if_not_exists(conn, schema, table, spark_schema):
    columns = []

    for field in spark_schema.fields:
        column_name = field.name
        postgres_type = spark_type_to_postgres(field.dataType)
        nullable = "" if field.nullable else "NOT NULL"
        columns.append(f"\"{column_name}\" {postgres_type} {nullable}")

    columns_sql = ",\n  ".join(columns)
    full_table = f"\"{schema}\".\"{table}\""
    query = f"CREATE SCHEMA IF NOT EXISTS \"{schema}\";\n" \
            f"CREATE TABLE IF NOT EXISTS {full_table} (\n  {columns_sql}\n);"

    with conn.cursor() as cursor:
        cursor.execute(query)
        conn.commit()


def export_table_to_csvs(catalog, schema, table):
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {TEMPORARY_CSVS_VOLUME}")

    df = spark.table(f"{catalog}.{schema}.{table}")
    df = df.filter(df["inserted_at"] > datetime.datetime.now() - datetime.timedelta(hours=1))
    csvs_path = os.path.join(TEMPORARY_CSVS_VOLUME_PATH, f"{table}_csv")

    logging.debug(f"Writing CSV to {csvs_path}.")

    df.write \
        .format("csv") \
        .option("header", "true") \
        .option("quote", "\"") \
        .option("escape", "\"") \
        .mode("overwrite") \
        .save(csvs_path)

    return csvs_path, df.schema


def load_csvs_to_postgres(pg_conn, s3_bucket, s3_paths, schema, table):
    full_table = f"\"{schema}\".\"{table}\""
    with pg_conn.cursor() as cursor:
        for s3_path in s3_paths:
            copy_sql = f"""
                SELECT aws_s3.table_import_from_s3(
                   '{full_table}',
                   '',
                   '(format csv, header)',
                   aws_commons.create_s3_uri('{s3_bucket}', '{s3_path}', 'us-east-1')
                );
            """
            logging.debug(f"Executing COPY command for {s3_path}.")
            cursor.execute(copy_sql)
        pg_conn.commit()


def delete_s3_files(s3_bucket, prefix):
    logging.debug(f"Deleting existing S3 files under prefix '{prefix}/'.")
    paginator = s3.get_paginator("list_objects_v2")
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
            s3.delete_objects(Bucket=s3_bucket, Delete={"Objects": chunk})
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


def export_schema_to_postgres(source_catalog,
                              source_schema,
                              target_schema,
                              s3_bucket,
                              s3_prefix):
    prefix = s3_prefix.strip("/")

    tables = [
        t.name for t in spark.catalog.listTables(f"{source_catalog}.{source_schema}")
        if t.tableType in ("MANAGED", "VIEW", "EXTERNAL", "TABLE")
    ]
    if not tables:
        logging.warning(f"No tables found in schema '{source_catalog}.{source_schema}'.")
        return

    logging.debug(f"Found tables: {tables}.")

    pg_conn = psycopg2.connect(
        host=pg_host,
        port=int(pg_port),
        dbname=pg_db,
        user=pg_user,
        password=pg_pass
    )

    empty_volume(TEMPORARY_CSVS_VOLUME_PATH)

    delete_s3_files(s3_bucket, prefix)

    try:
        with pg_conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;")
            pg_conn.commit()

        for table in tables:
            logging.info(f"Processing table: {table}.")

            local_path_to_csvs, spark_schema = export_table_to_csvs(
                source_catalog, source_schema, table)

            s3_paths = []

            for file_name in os.listdir(local_path_to_csvs):
                if not file_name.endswith(".csv"):
                    continue
                local_file_path = os.path.join(local_path_to_csvs, file_name)
                s3_key = f"{prefix}/{table}/{file_name}"
                logging.debug(f"Uploading {local_file_path} to s3://{s3_bucket}/{s3_key}.")
                s3.upload_file(local_file_path, s3_bucket, s3_key)
                s3_paths.append(s3_key)

            logging.debug("Ensuring Postgres table exists (best-effort mapping from Spark types).")
            create_table_if_not_exists(pg_conn, target_schema, table, spark_schema)

            load_csvs_to_postgres(pg_conn, s3_bucket, s3_paths, target_schema, table)

            for file_name in os.listdir(local_path_to_csvs):
                local_file_path = os.path.join(local_path_to_csvs, file_name)
                os.remove(local_file_path)
            os.rmdir(local_path_to_csvs)

            logging.info(f"Finished table: {table}.")
    finally:
        pg_conn.close()

    delete_s3_files(s3_bucket, prefix)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-catalog", required=True)
    parser.add_argument("--source-schema", required=True)
    parser.add_argument("--secret-scope", required=True)
    parser.add_argument("--s3-bucket-name", required=True)

    args = parser.parse_args()

    spark = get_spark()
    dbutils = DBUtils(spark)

    aws_access_key = get_secret(AWS_ACCESS_KEY_SECRET)
    aws_secret_key = get_secret(AWS_SECRET_KEY_SECRET)

    pg_host = get_secret(PG_HOST_SECRET)
    pg_port = get_secret(PG_PORT_SECRET)
    pg_db = get_secret(PG_DB_SECRET)
    pg_user = get_secret(PG_USER_SECRET)
    pg_pass = get_secret(PG_PASS_SECRET)

    boto3_kwargs = {
        "aws_access_key_id": aws_access_key,
        "aws_secret_access_key": aws_secret_key,
    }
    s3 = boto3.client("s3", **boto3_kwargs)

    export_schema_to_postgres(source_catalog=args.source_catalog,
                              source_schema=args.source_schema,
                              target_schema=args.source_schema,
                              s3_bucket=args.s3_bucket_name,
                              s3_prefix=S3_PREFIX)

    logging.info("All done.")
