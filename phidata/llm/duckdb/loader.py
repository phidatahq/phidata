from typing import Tuple

from phidata.utils.log import logger

try:
    import duckdb
except ImportError:
    logger.warning("DuckDB not available.")
    raise


def load_s3_path_to_table(
    duckdb_connection: duckdb.DuckDBPyConnection, load_s3_path: str
) -> Tuple[str, str]:
    """
    Load a file from S3 into duckdb

    Args:
        duckdb_connection (duckdb.DuckDBPyConnection): duckdb connection
        load_s3_path (str): S3 path to load

    Returns:
        str: Table name
        str: SQL statement used to load the file
    """
    import os

    # Get the file name from the s3 path
    file_name = load_s3_path.split("/")[-1]
    # Get the file name without extension from the s3 path
    table_name, extension = os.path.splitext(file_name)
    # If the table_name isn't a valid SQL identifier, we'll need to use something else
    table_name = (
        table_name.replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )

    create_statement = (
        f"CREATE OR REPLACE TABLE '{table_name}' AS SELECT * FROM '{load_s3_path}';"
    )
    duckdb_connection.sql(create_statement)

    return table_name, create_statement
