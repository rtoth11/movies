from datetime import datetime, timezone, timedelta
import io
import json
import os

import boto3
import pandas as pd
import psycopg2

WATERMARK_KEY = "watermark/last_watermark.json"
EXPORT_LAG = timedelta(minutes=5)  # guard against open transactions


def _pg_connect():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def get_watermark(s3, s3_bucket, watermark_key=WATERMARK_KEY) -> datetime:

    try:
        obj = s3.get_object(Bucket=s3_bucket, Key=watermark_key)
        ts = json.loads(obj["Body"].read())["last_exported_at"]
        return datetime.fromisoformat(ts)
    except s3.exceptions.NoSuchKey:
        return datetime(2020, 1, 1, tzinfo=timezone.utc)


def run_export(s3_bucket, schema, pg_export_s3_path, watermark_key=WATERMARK_KEY):
    s3 = boto3.client("s3")
    conn = _pg_connect()

    last_exported_at = get_watermark(s3, s3_bucket)
    export_cutoff = datetime.now(timezone.utc) - EXPORT_LAG

    df = pd.read_sql(
        f"""
            SELECT * FROM "{schema}"."searches"
            WHERE created_at >= %(since)s
              AND created_at < %(until)s
            ORDER BY created_at
        """,
        conn,
        params={"since": last_exported_at, "until": export_cutoff}
    )

    if df.empty:
        print("No new rows - skipping export")
        return

    date_str = export_cutoff.strftime("%Y%m%d")
    ts_str = export_cutoff.strftime("%Y%m%d_%H%M%S")
    key = f"{pg_export_s3_path}/date={date_str}/searches_{ts_str}.json"

    buffer = io.BytesIO()
    df.to_json(buffer, orient="records", lines=True, index=False)
    s3.put_object(Bucket=s3_bucket, Key=key, Body=buffer.getvalue())

    # Update watermark only after successful upload
    s3.put_object(
        Bucket=s3_bucket,
        Key=watermark_key,
        Body=json.dumps({"last_exported_at": export_cutoff.isoformat()})
    )
    print(f"Exported {len(df)} rows up to {export_cutoff}")


def handler(event, context):
    s3_bucket = event.get("s3_bucket")
    pg_export_s3_path = event.get("pg_export_s3_path")
    schema = event.get("schema")
    run_export(s3_bucket, schema, pg_export_s3_path)
