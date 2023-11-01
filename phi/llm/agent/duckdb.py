from typing import Optional, Tuple

from phi.llm.agent.base import BaseAgent
from phi.utils.log import logger

try:
    import duckdb
except ImportError:
    raise ImportError("`duckdb` not installed. Please install it using `pip install duckdb`.")


class DuckDbAgent(BaseAgent):
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
        self.register(self.inspect_query)
        self.register(self.describe_table_or_view)
        self.register(self.export_table_as)
        self.register(self.summarize_table)
        self.register(self.create_fts_index)
        self.register(self.full_text_search)

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
            logger.debug(f"Running query: {formatted_sql}")

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

            logger.debug(f"Query result: {result_output}")
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
        stmt = "SHOW TABLES;"
        tables = self.run_duckdb_query(stmt)
        logger.debug(f"Tables: {tables}")
        return tables

    def describe_table(self, table: str) -> str:
        """Function to describe a table

        :param table: Table to describe
        :return: Description of the table
        """
        stmt = f"DESCRIBE {table};"
        table_description = self.run_duckdb_query(stmt)

        logger.debug(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def summarize_table(self, table: str) -> str:
        """Function to summarize the contents of a table

        :param table: Table to describe
        :return: Description of the table
        """
        stmt = f"SUMMARIZE SELECT * FROM {table};"
        table_description = self.run_duckdb_query(stmt)

        logger.debug(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def inspect_query(self, query: str) -> str:
        """Function to inspect a query and return the query plan. Always inspect your query before running them.

        :param query: Query to inspect
        :return: Qeury plan
        """
        stmt = f"explain {query};"
        explain_plan = self.run_duckdb_query(stmt)

        logger.debug(f"Explain plan: {explain_plan}")
        return explain_plan

    def describe_table_or_view(self, table: str):
        """Function to describe a table or view

        :param table: Table or view to describe
        :return: Description of the table or view
        """
        stmt = f"select column_name, data_type from information_schema.columns where table_name='{table}';"
        table_description = self.run_duckdb_query(stmt)

        logger.debug(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def load_local_path_to_table(self, path: str, table_name: Optional[str] = None) -> Tuple[str, str]:
        """Load a local file into duckdb

        :param path: Path to load
        :param table_name: Optional table name to use
        :return: Table name, SQL statement used to load the file
        """
        import os

        logger.debug(f"Loading {path} into duckdb")

        if table_name is None:
            # Get the file name from the s3 path
            file_name = path.split("/")[-1]
            # Get the file name without extension from the s3 path
            table_name, extension = os.path.splitext(file_name)
            # If the table_name isn't a valid SQL identifier, we'll need to use something else
            table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")

        create_statement = f"CREATE OR REPLACE TABLE '{table_name}' AS SELECT * FROM '{path}';"
        self.run_duckdb_query(create_statement)

        logger.debug(f"Loaded {path} into duckdb as {table_name}")
        # self.run_duckdb_query(f"SELECT * from {table_name};")
        return table_name, create_statement

    def load_local_csv_to_table(
        self, path: str, table_name: Optional[str] = None, delimiter: Optional[str] = None
    ) -> Tuple[str, str]:
        """Load a local CSV file into duckdb

        :param path: Path to load
        :param table_name: Optional table name to use
        :param delimiter: Optional delimiter to use
        :return: Table name, SQL statement used to load the file
        """
        import os

        logger.debug(f"Loading {path} into duckdb")

        if table_name is None:
            # Get the file name from the s3 path
            file_name = path.split("/")[-1]
            # Get the file name without extension from the s3 path
            table_name, extension = os.path.splitext(file_name)
            # If the table_name isn't a valid SQL identifier, we'll need to use something else
            table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")

        select_statement = f"SELECT * FROM read_csv('{path}'"
        if delimiter is not None:
            select_statement += f", delim='{delimiter}')"
        else:
            select_statement += ")"

        create_statement = f"CREATE OR REPLACE TABLE '{table_name}' AS {select_statement};"
        self.run_duckdb_query(create_statement)

        logger.debug(f"Loaded CSV {path} into duckdb as {table_name}")
        # self.run_duckdb_query(f"SELECT * from {table_name};")
        return table_name, create_statement

    def load_s3_path_to_table(self, s3_path: str, table_name: Optional[str] = None) -> Tuple[str, str]:
        """Load a file from S3 into duckdb

        :param s3_path: S3 path to load
        :param table_name: Optional table name to use
        :return: Table name, SQL statement used to load the file
        """
        import os

        logger.debug(f"Loading {s3_path} into duckdb")

        if table_name is None:
            # Get the file name from the s3 path
            file_name = s3_path.split("/")[-1]
            # Get the file name without extension from the s3 path
            table_name, extension = os.path.splitext(file_name)
            # If the table_name isn't a valid SQL identifier, we'll need to use something else
            table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")

        create_statement = f"CREATE OR REPLACE TABLE '{table_name}' AS SELECT * FROM '{s3_path}';"
        self.run_duckdb_query(create_statement)

        logger.debug(f"Loaded {s3_path} into duckdb as {table_name}")
        # self.run_duckdb_query(f"SELECT * from {table_name};")
        return table_name, create_statement

    def load_s3_csv_to_table(
        self, s3_path: str, table_name: Optional[str] = None, delimiter: Optional[str] = None
    ) -> Tuple[str, str]:
        """Load a CSV file from S3 into duckdb

        :param s3_path: S3 path to load
        :param table_name: Optional table name to use
        :return: Table name, SQL statement used to load the file
        """
        import os

        logger.debug(f"Loading {s3_path} into duckdb")

        if table_name is None:
            # Get the file name from the s3 path
            file_name = s3_path.split("/")[-1]
            # Get the file name without extension from the s3 path
            table_name, extension = os.path.splitext(file_name)
            # If the table_name isn't a valid SQL identifier, we'll need to use something else
            table_name = table_name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")

        select_statement = f"SELECT * FROM read_csv('{s3_path}'"
        if delimiter is not None:
            select_statement += f", delim='{delimiter}')"
        else:
            select_statement += ")"

        create_statement = f"CREATE OR REPLACE TABLE '{table_name}' AS {select_statement};"
        self.run_duckdb_query(create_statement)

        logger.debug(f"Loaded CSV {s3_path} into duckdb as {table_name}")
        # self.run_duckdb_query(f"SELECT * from {table_name};")
        return table_name, create_statement

    def export_table_as(self, table_name: str, format: Optional[str] = "PARQUET", path: Optional[str] = None) -> str:
        """Save a table to a desired format
        The function will use the default format as parquet
        If the path is provided, the table will be exported to that path, example s3

        :param table_name: Table to export
        :param format: Format to export to
        :param path: Path to export to
        :return: None
        """
        if format is None:
            format = "PARQUET"

        logger.debug(f"Exporting Table {table_name} as {format.upper()} in the path {path}")
        # self.run_duckdb_query(f"SELECT * from {table_name};")
        if path is None:
            path = f"{table_name}.{format}"
        else:
            path = f"{path}/{table_name}.{format}"
        export_statement = f"COPY (SELECT * FROM {table_name}) TO '{path}' (FORMAT {format.upper()});"
        result = self.run_duckdb_query(export_statement)
        logger.debug(f"Exported {table_name} to {path}/{table_name}")

        return result

    def create_fts_index(self, table_name: str, unique_key: str, input_values: list[str]) -> str:
        """Create a full text search index on a table

        :param table_name: Table to create the index on
        :param unique_key: Unique key to use
        :param input_values: Values to index
        :return: None
        """
        logger.debug(f"Creating FTS index on {table_name} for {input_values}")
        self.run_duckdb_query("INSTALL fts;")
        logger.debug("Installed FTS extension")
        self.run_duckdb_query("LOAD fts;")
        logger.debug("Loaded FTS extension")

        create_fts_index_statement = f"PRAGMA create_fts_index('{table_name}', '{unique_key}', '{input_values}');"
        logger.debug(f"Running {create_fts_index_statement}")
        result = self.run_duckdb_query(create_fts_index_statement)
        logger.debug(f"Created FTS index on {table_name} for {input_values}")

        return result

    def full_text_search(self, table_name: str, unique_key: str, search_text: str) -> str:
        """Full text Search in a table column for a specific text/keyword

        :param table_name: Table to search
        :param unique_key: Unique key to use
        :param search_text: Text to search
        :return: None
        """
        logger.debug(f"Running full_text_search for {search_text} in {table_name}")
        search_text_statement = f"""SELECT fts_main_corpus.match_bm25({unique_key}, '{search_text}') AS score,*
                                    FROM {table_name}
                                    WHERE score IS NOT NULL
                                    ORDER BY score;"""

        logger.debug(f"Running {search_text_statement}")
        result = self.run_duckdb_query(search_text_statement)
        logger.debug(f"Search results for {search_text} in {table_name}")

        return result
