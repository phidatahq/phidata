from phidata.utils.log import logger

try:
    import duckdb
except ImportError:
    logger.warning("DuckDB not available.")
    raise


def run_duckdb_query(
    duckdb_connection: duckdb.DuckDBPyConnection, sql_query: str
) -> str:
    """
    Function to run SQL queries against a duckdb database

    Args:
        duckdb_connection (duckdb.DuckDBPyConnection): duckdb connection
        sql_query (str): SQL query to run

    Returns:
        str: Result of the query
    """
    # -*- Format the SQL Query
    # Remove backticks
    formatted_sql = sql_query.replace("`", "")
    # If there are multiple statements, only run the first one
    formatted_sql = formatted_sql.split(";")[0]

    try:
        query_result = duckdb_connection.sql(formatted_sql)
        result_output = "No output"
        if query_result is not None:
            try:
                results_as_python_objects = query_result.fetchall()
                result_rows = []
                for row in results_as_python_objects:
                    if len(row) == 1:
                        result_rows.append(str(row[0]))
                    else:
                        result_rows.append(",".join(str(x) for x in row))

                result_data = "\n".join(result_rows)
                result_output = ",".join(query_result.columns) + "\n" + result_data
            except AttributeError:
                result_output = str(query_result)
        return result_output
    except duckdb.ProgrammingError as e:
        return str(e)
    except duckdb.Error as e:
        return str(e)
    except Exception as e:
        return str(e)


def describe_table_or_view(duckdb_connection: duckdb.DuckDBPyConnection, table: str):
    """
    Function to describe a table or view

    Args:
        duckdb_connection (duckdb.DuckDBPyConnection): duckdb connection
        table (str): Table or view to describe

    Returns:
        str: Description of the table or view
    """
    statement = f"select column_name, data_type from information_schema.columns where table_name='{table}';"
    table_description = run_duckdb_query(duckdb_connection, statement)
    return f"{table}\n{table_description}"
