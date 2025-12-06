import argparse
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

    args = parser.parse_args()

    spark = get_spark()
    dbutils = DBUtils(spark)

    if not os.path.exists(args.movie_data_volume_path) \
            or len(os.listdir(args.movie_data_volume_path)) == 0:
        return

    df = spark.read.option("multiline","true").json(f"{args.movie_data_volume_path}*")

    if len(df.head(1)) > 0:
        if not spark.catalog.tableExists("movies.bronze.bronze_json_movies"):
            df.write.mode("overwrite").saveAsTable("movies.bronze.bronze_json_movies")
        else:
            df.write.mode("append").saveAsTable("movies.bronze.bronze_json_movies")

    dbutils.fs().rm(args.movie_data_volume_path, True)


if __name__ == "__main__":
    main()
