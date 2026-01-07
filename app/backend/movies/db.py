import os

from psycopg2.pool import SimpleConnectionPool

from . import SCHEMA_NAME

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DB = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")

pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=PG_HOST,
    port=int(PG_PORT),
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD,
    options=f"-c search_path={SCHEMA_NAME}"
)


def query(sql, params=None):
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
    finally:
        pool.putconn(conn)
