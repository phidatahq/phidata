from typing import Optional, Tuple

from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger

try:
    import duckdb
except ImportError:
    raise ImportError("`duckdb` not installed. Please install it using `pip install duckdb`.")


class DuckDbAgent(FunctionRegistry):
    def __init__(
        self,
        db_path: str = ":memory:",
        s3_region: str = "us-east-1",
        duckdb_connection: Optional[duckdb.DuckDBPyConnection] = None,
    ):
        super().__init__(name="duckdb_registry")

        self.db_path: str = db_path
        self.s3_region: str = s3_region
        self._duckdb_connection: Optional[duckdb.DuckDBPyConnection] = duckdb_connection

        self.register(self.run_duckdb_query)
        self.register(self.show_tables)
        self.register(self.describe_table)
        self.register(self.explain_query)
        self.register(self.describe_table_or_view)

    @property
    def duckdb_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Returns the duckdb connection

        :return duckdb.DuckDBPyConnection: duckdb connection
        """
        if self._duckdb_connection is None:
            self._duckdb_connection = duckdb.connect(self.db_path)
            try:
                self._duckdb_connection.sql("INSTALL httpfs;")
                self._duckdb_connection.sql("LOAD httpfs;")
                self._duckdb_connection.sql(f"SET s3_region='{self.s3_region}';")
            except Exception as e:
                logger.exception(e)
                logger.warning("Failed to install httpfs extension. Only local files will be supported")

        return self._duckdb_connection

    def run_duckdb_query(self, query: str) -> str:
        """Function to run SQL queries against a duckdb database

        :param query: SQL query to run
        :return: Result of the query
        """

        # -*- Format the SQL Query
        # Remove backticks
        formatted_sql = query.replace("`", "")
        # If there are multiple statements, only run the first one
        formatted_sql = formatted_sql.split(";")[0]

        try:
            logger.info(f"Running query: {formatted_sql}")

            query_result = self.duckdb_connection.sql(formatted_sql)
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

            logger.info(f"Query result: {result_output}")
            return result_output
        except duckdb.ProgrammingError as e:
            return str(e)
        except duckdb.Error as e:
            return str(e)
        except Exception as e:
            return str(e)

    def show_tables(self) -> str:
        """Function to show tables in the database

        :return: List of tables in the database
        """
        stmt = "select table_name from information_schema.tables where table_schema='public';"
        tables = self.run_duckdb_query(stmt)
        logger.info(f"Tables: {tables}")
        return tables

    def describe_table(self, table: str) -> str:
        """Function to describe a table

        :param table: Table to describe
        :return: Description of the table
        """
        stmt = f"select column_name, data_type from information_schema.columns where table_name='{table}';"
        table_description = self.run_duckdb_query(stmt)

        logger.info(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def explain_query(self, query: str) -> str:
        """Function to explain the query plan. Always explain your query before execution.

        :param query: Query to validate
        :return: Validation result
        """
        stmt = f"explain {query};"
        explain_plan = self.run_duckdb_query(stmt)

        logger.info(f"Explain plan: {explain_plan}")
        return explain_plan

    def describe_table_or_view(self, table: str):
        """Function to describe a table or view

        :param table: Table or view to describe
        :return: Description of the table or view
        """
        stmt = f"select column_name, data_type from information_schema.columns where table_name='{table}';"
        table_description = self.run_duckdb_query(stmt)

        logger.info(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def load_s3_path_to_table(self, load_s3_path: str) -> Tuple[str, str]:
        """Load a file from S3 into duckdb

        :param load_s3_path: S3 path to load
        :return: Table name, SQL statement used to load the file
        """
        import os

        # Get the file name from the s3 path
        file_name = load_s3_path.split("/")[-1]
        # Get the file name without extension from the s3 path
        table_name, extension = os.path.splitext(file_name)
        # If the table_name isn't a valid SQL identifier, we'll need to use something else
        table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")

        create_statement = f"CREATE OR REPLACE TABLE '{table_name}' AS SELECT * FROM '{load_s3_path}';"
        self.duckdb_connection.sql(create_statement)

        return table_name, create_statement
