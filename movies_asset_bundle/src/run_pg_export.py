import argparse
import json
import logging

import boto3
from pyspark.dbutils import DBUtils

from databricks_to_postgres import get_secret, get_spark, AWS_ACCESS_KEY_SECRET, AWS_SECRET_KEY_SECRET


def invoke_pg_export_lambda(lambda_name, target_schema, s3_bucket, pg_export_s3_path):
    payload = {
        "schema": target_schema,
        "s3_bucket": s3_bucket,
        "pg_export_s3_path": pg_export_s3_path,
    }

    logging.info(f"Invoking Lambda '{lambda_name}'.")
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType="RequestResponse",   # synchronous — wait for completion
        Payload=json.dumps(payload).encode(),
    )

    status_code = response["StatusCode"]
    response_payload = json.loads(response["Payload"].read())

    got_error = response_payload \
                and (
                        response_payload.get("FunctionError")
                        or response_payload.get("ErrorMessage")
                )
    if status_code != 200 or got_error:
        raise RuntimeError(
            f"Lambda invocation failed (HTTP {status_code}): {response_payload}."
        )

    logging.info(f"Lambda response: {response_payload}.")
    return response_payload


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--s3-bucket-name", required=True)
    parser.add_argument("--pg-export-s3-path", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--lambda-name", required=True,
                        help="Name of the pg-export Lambda function")
    parser.add_argument("--aws-region", default="us-east-1")
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
    lambda_client = boto3.client("lambda", **boto3_kwargs, region_name=args.aws_region)

    invoke_pg_export_lambda(
        lambda_name=args.lambda_name,
        target_schema=args.schema,
        s3_bucket=args.s3_bucket_name,
        pg_export_s3_path=args.pg_export_s3_path,
    )
