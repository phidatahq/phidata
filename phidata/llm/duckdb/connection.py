from phidata.utils.log import logger

try:
    import duckdb
except ImportError:
    logger.warning("DuckDB not available.")
    raise


def create_duckdb_connection(
    db_path: str = ":memory:", s3_region: str = "us-east-1"
) -> duckdb.DuckDBPyConnection:
    """
    Create a duckdb connection

    Args:
        db_path (str, optional): Path to the database. Defaults to ":memory:".
        s3_region (str, optional): S3 region. Defaults to "us-east-1".

    Returns:
        duckdb.DuckDBPyConnection: duckdb connection
    """
    duckdb_connection = duckdb.connect(db_path)
    try:
        duckdb_connection.sql("INSTALL httpfs;")
        duckdb_connection.sql("LOAD httpfs;")
        duckdb_connection.sql(f"SET s3_region='{s3_region}';")
    except Exception:
        logger.warning(
            "Failed to install httpfs extension. Only local files will be supported"
        )

    return duckdb_connection
