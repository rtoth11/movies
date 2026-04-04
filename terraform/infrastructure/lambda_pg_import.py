"""
Invoked by the Databricks export script instead of connecting directly to RDS.
Receives a list of (s3_key, target_schema, target_table) tuples plus schema
DDL info, creates tables if needed, runs aws_s3.table_import_from_s3, and
refreshes the materialized view.

Expected event shape:
{
  "target_schema": "gold",
  "s3_bucket": "my-movies-bucket",
  "region": "us-east-1",
  "tables": [
    {
      "table": "gold_dialogues",
      "s3_keys": ["databricks_exports/gold_dialogues/part-0.csv", ...],
      "columns": [
        {"name": "id", "type": "BIGINT", "nullable": true},
        ...
      ]
    },
    ...
  ],
  "refresh_materialized_view": true   # optional, default true
}
"""

import logging
import os

import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CREATE_EXTENSIONS_SQL = """
    CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;
    CREATE EXTENSION IF NOT EXISTS pg_trgm CASCADE;
"""


def _pg_connect():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def _create_table_if_not_exists(cursor, schema, table, columns):
    col_defs = ", ".join(
        f"\"{c['name']}\" {c['type']}{'' if c.get('nullable', True) else ' NOT NULL'}"
        for c in columns
    )
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS \"{schema}\";")
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS \"{schema}\".\"{table}\" ({col_defs});"
    )


def _load_s3_keys(cursor, s3_bucket, s3_keys, schema, table, region):
    full_table = f"\"{schema}\".\"{table}\""
    for s3_key in s3_keys:
        copy_sql = f"""
            SELECT aws_s3.table_import_from_s3(
               '{full_table}',
               '',
               '(format csv, header)',
               aws_commons.create_s3_uri('{s3_bucket}', '{s3_key}', '{region}')
            );
        """
        logger.info(f"Importing s3://{s3_bucket}/{s3_key} to {full_table}.")
        cursor.execute(copy_sql)


def _refresh_materialized_view(cursor, schema):
    create_view_sql = f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS "{schema}"."all_tables" AS

        (SELECT
            'dialogue' AS type,
            d.id AS block_id,
            d.movie_tmdb_id,
            d.index_in_script,
            d.dialogue AS content,
            d.suffix,
            d.parentheticals,
            c.id AS character_id,
            c.name AS character,
            to_tsvector('english', d.dialogue) AS search_vector
        FROM "{schema}"."gold_dialogues" d
        JOIN "{schema}".gold_characters c ON d.character_id = c.id)

        UNION ALL

        (SELECT
            'description',
            id,
            movie_tmdb_id,
            index_in_script,
            description,
            NULL, NULL, NULL, NULL,
            to_tsvector('english', description)
        FROM "{schema}"."gold_descriptions")

        UNION ALL

        (SELECT
            'scene',
            id,
            movie_tmdb_id,
            index_in_script,
            scene,
            NULL, NULL, NULL, NULL,
            to_tsvector('english', scene)
        FROM "{schema}"."gold_scenes")

        UNION ALL

        (SELECT
            'unknown',
            id,
            movie_tmdb_id,
            index_in_script,
            content,
            NULL, NULL, NULL, NULL,
            to_tsvector('english', content)
        FROM "{schema}"."gold_unknown_blocks");
    """

    cursor.execute(create_view_sql)
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_all_tables_movie_tmdb_id "
        f"ON \"{schema}\".\"all_tables\" (movie_tmdb_id);"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_all_tables_search_vector "
        f"ON \"{schema}\".\"all_tables\" USING GIN(search_vector);"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_all_tables_dialogue_trigram "
        f"ON \"{schema}\".\"all_tables\" USING GIN (content gin_trgm_ops);"
    )
    cursor.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_all_tables_unique "
        f"ON \"{schema}\".\"all_tables\" (block_id);"
    )
    cursor.execute(
        f"REFRESH MATERIALIZED VIEW CONCURRENTLY \"{schema}\".\"all_tables\";"
    )
    logger.info("Materialized view 'all_tables' refreshed.")


def handler(event, context):
    target_schema = event["target_schema"]
    s3_bucket = event.get("s3_bucket", os.environ.get("S3_BUCKET"))
    region = event.get("region", os.environ.get("REGION", "us-east-1"))
    tables = event["tables"]
    refresh_view = event.get("refresh_materialized_view", True)

    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_EXTENSIONS_SQL)
        conn.commit()

        for table_spec in tables:
            table = table_spec["table"]
            s3_keys = table_spec["s3_keys"]
            columns = table_spec["columns"]

            with conn.cursor() as cur:
                _create_table_if_not_exists(cur, target_schema, table, columns)
                _load_s3_keys(cur, s3_bucket, s3_keys, target_schema, table, region)
            conn.commit()
            logger.info(f"Finished importing table: {table}")

        if refresh_view and tables:
            with conn.cursor() as cur:
                _refresh_materialized_view(cur, target_schema)
            conn.commit()

    finally:
        conn.close()

    return {"status": "ok", "tables_imported": len(tables)}
