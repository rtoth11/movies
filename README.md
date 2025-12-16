GitHub secrets required:
- AWS_ACCESS_KEY_ID: needed to create the permissions_for_hcp_terraform resources
- AWS_SECRET_ACCESS_KEY: needed to create the permissions_for_hcp_terraform resources
- TF_API_TOKEN: needed to authenticate with HCP Terraform
- TMDB_API_KEY: needed to authenticate with TMDB
- DATABRICKS_HOST: needed to upload files to Databricks
- DATABRICKS_TOKEN: needed to authenticate with Databricks (free edition doesn't have OIDC option)
- PG_DATABASE: PostgreSQL database name for the RDS instance
- PG_USER: PostgreSQL username for the RDS instance
- PG_PASSWORD: PostgreSQL password for the RDS instance

GitHub variables required:
- DATABRICKS_MOVIE_DATA_VOLUME_PATH: where to upload files in Databricks
