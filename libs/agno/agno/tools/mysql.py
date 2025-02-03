from typing import Any, Dict, Optional
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse
from agno.tools import Toolkit
from agno.utils.log import logger

class MySQLTools(Toolkit):
    """A basic tool to connect to a MySQL database and perform read-only operations on it."""
    def __init__(
        self,
        db_url: Optional[str] = None,
        connection: Optional[mysql.connector.connection.MySQLConnection] = None,
        db_name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        run_queries: bool = True,
        inspect_queries: bool = False,
        summarize_tables: bool = True,
        export_tables: bool = False,
        allow_write_operations: bool = False  # New parameter to block write operations
    ):
        super().__init__(name="mysql_tools")
        self._connection: Optional[mysql.connector.connection.MySQLConnection] = connection
        self.db_name: Optional[str] = db_name
        self.user: Optional[str] = user
        self.password: Optional[str] = password
        self.host: Optional[str] = host
        self.port: Optional[int] = port
        self.allow_write_operations = allow_write_operations  # Store the flag

        # Parse db_url if provided
        if db_url:
            parsed_url = urlparse(db_url)
            self.user = parsed_url.username
            self.password = parsed_url.password
            self.host = parsed_url.hostname
            self.port = parsed_url.port or 3306  # Default MySQL port
            self.db_name = parsed_url.path.strip("/")

        # Register tools
        self.register(self.show_tables)
        self.register(self.describe_table)
        if inspect_queries:
            self.register(self.inspect_query)
        if run_queries:
            self.register(self.run_query)
        if summarize_tables:
            self.register(self.summarize_table)
        if export_tables:
            self.register(self.export_table_to_path)

    @property
    def connection(self) -> mysql.connector.connection.MySQLConnection:
        """
        Returns the MySQL connection.
        :return mysql.connector.connection.MySQLConnection: MySQL connection
        """
        if self._connection is None:
            connection_kwargs: Dict[str, Any] = {}
            if self.db_name is not None:
                connection_kwargs["database"] = self.db_name
            if self.user is not None:
                connection_kwargs["user"] = self.user
            if self.password is not None:
                connection_kwargs["password"] = self.password
            if self.host is not None:
                connection_kwargs["host"] = self.host
            if self.port is not None:
                connection_kwargs["port"] = self.port
            self._connection = mysql.connector.connect(**connection_kwargs)
            self._connection.autocommit = True  # Ensure read-only mode
        return self._connection

    def show_tables(self) -> str:
        """Function to show tables in the database.
        :return: List of tables in the database
        """
        stmt = "SHOW TABLES;"
        tables = self.run_query(stmt)
        logger.debug(f"Tables: {tables}")
        return tables

    def describe_table(self, table: str) -> str:
        """Function to describe a table.
        :param table: Table to describe
        :return: Description of the table
        """
        stmt = f"DESCRIBE {table};"
        table_description = self.run_query(stmt)
        logger.debug(f"Table description: {table_description}")
        return f"{table}\n{table_description}"

    def summarize_table(self, table: str) -> str:
        """
        Function to compute summary statistics for numeric columns in a table.
        :param table: Table to summarize
        :return: Summary of the table
        """
        stmt = f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table}' AND TABLE_SCHEMA = '{self.db_name}';
        """
        column_info = self.run_query(stmt)
        logger.debug(f"Column info: {column_info}")

        numeric_columns = []
        for row in column_info.split("\n"):
            if not row:
                continue
            column_name, data_type = row.split(",")
            if data_type.strip() in ("int", "decimal", "float", "double"):
                numeric_columns.append(column_name.strip())

        summary_queries = []
        for column in numeric_columns:
            summary_queries.append(
                f"SELECT '{column}' AS column_name, MIN({column}) AS min, MAX({column}) AS max, AVG({column}) AS avg, COUNT(*) AS count FROM {table};"
            )

        summary_results = []
        for query in summary_queries:
            result = self.run_query(query)
            summary_results.append(result)

        return "\n".join(summary_results)

    def run_query(self, query: str) -> str:
        """Function that runs a query and returns the result.
        :param query: SQL query to run
        :return: Result of the query
        """
        formatted_sql = query.replace("`", "").split(";")[0]

        # Check for restricted keywords if write operations are not allowed
        if not self.allow_write_operations:
            restricted_keywords = ["INSERT", "UPDATE", "DELETE"]
            sql_query_upper = formatted_sql.upper()
            for keyword in restricted_keywords:
                if keyword in sql_query_upper:
                    logger.warning(f"Blocked unsafe query: {keyword} operation is not allowed.")
                    return f"Error: {keyword} operation is not allowed."

        try:
            logger.info(f"Executing SQL: {formatted_sql}")
            cursor = self.connection.cursor()
            cursor.execute(formatted_sql)
            query_result = cursor.fetchall()

            if not query_result:
                return "No results found for the given query."

            result_rows = []
            for row in query_result:
                if len(row) == 1:
                    result_rows.append(str(row[0]))
                else:
                    result_rows.append(", ".join(str(x) for x in row))
            result_data = "\n".join(result_rows)

            logger.debug(f"Query result: {result_data}")
            return result_data

        except Error as e:
            logger.error(f"Error executing query: {e}")
            return f"Error executing query: {str(e)}"
