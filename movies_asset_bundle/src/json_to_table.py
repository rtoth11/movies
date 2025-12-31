import argparse
import datetime
import logging
import os

from pyspark.dbutils import DBUtils
from pyspark.sql import SparkSession


def get_spark() -> SparkSession:
    try:
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.getOrCreate()
    except ImportError:
        return SparkSession.builder.getOrCreate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--movie-data-volume-path", required=True)
    parser.add_argument("--bronze-schema-name", required=True)
    parser.add_argument("--asset-bundle-target", required=True)

    args = parser.parse_args()

    spark = get_spark()
    dbutils = DBUtils(spark)

    if not os.path.exists(args.movie_data_volume_path) \
            or len(os.listdir(args.movie_data_volume_path)) == 0:
        logging.info("No movie data found to process. Exiting.")
        return

    df = spark.read.option("multiline","true").json(f"{args.movie_data_volume_path}*")

    bronze_schema_name = args.bronze_schema_name

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS movies.{bronze_schema_name}")

    if len(df.head(1)) > 0:
        if not spark.catalog.tableExists(f"movies.{bronze_schema_name}.bronze_json_movies"):
            df.write.mode("overwrite").saveAsTable(
                f"movies.{bronze_schema_name}.bronze_json_movies"
            )
        else:
            df.write.mode("append").saveAsTable(f"movies.{bronze_schema_name}.bronze_json_movies")

    if args.asset_bundle_target == "prod":
        spark.sql("CREATE SCHEMA IF NOT EXISTS movies.processed_jsons")
        spark.sql("CREATE VOLUME IF NOT EXISTS movies.processed_jsons.archive")

        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = f"/Volumes/movies/processed_jsons/archive/{current_time}"
        dbutils.fs.mkdirs(target_path)
        dbutils.fs.cp(args.movie_data_volume_path,
                      target_path,
                      True)

    dbutils.fs().rm(args.movie_data_volume_path, True)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    main()
