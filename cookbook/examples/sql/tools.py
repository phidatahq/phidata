from os import getenv
import json
from typing import List, Optional

from phi.tools import Toolkit
from sqlalchemy import create_engine
from sqlalchemy.schema import Table, MetaData
from sqlalchemy.sql.expression import select, text
from trino.sqlalchemy import URL

from utils.log import logger


class TrinoTools(Toolkit):
    def __init__(self):
        super().__init__(name="trino_tools")

        trino_host: str = getenv("TRINO_HOST")
        trino_port: int = int(getenv("TRINO_PORT"))
        trino_user: str = getenv("TRINO_USER")
        trino_password: str = getenv("TRINO_PASSWORD")
        trino_catalog: str = getenv("TRINO_CATALOG")
        trino_schema: str = getenv("TRINO_SCHEMA")
        trino_role: str = getenv("TRINO_ROLE")

        connection_url = URL(
            host=trino_host,
            port=trino_port,
            user=trino_user,
            password=trino_password,
            catalog=trino_catalog,
            schema=trino_schema,
        )
        connection_args = {
            "roles": {trino_catalog: trino_role},
            "http_scheme": "https",
        }
        self.engine = create_engine(url=connection_url, connect_args=connection_args)
        self.connection = self.engine.connect()
        # self.register(self.list_tables)
        self.register(self.describe_table)
        self.register(self.run_query)

    def _run_sql(self, sql: str, limit: Optional[int] = None) -> List[dict]:
        """Internal function to run a sql query.

        Args:
            sql (str): The sql query to run.
            limit (int, optional): The limit of the result. Defaults to 10. Use None to show all results.

        Returns:
            List[dict]: The result of the query.
        """
        logger.debug(f"Running sql |\n{sql}")

        if limit is None:
            _result = self.connection.execute(text(sql)).fetchall()
        else:
            _result = self.connection.execute(text(sql)).fetchmany(limit)

        _result_dict = [row._asdict() for row in _result]
        logger.debug(f"sql result: {_result_dict}")

        return _result_dict

    def list_tables(self) -> str:
        """
        Use this function to get the list of tables.

        Returns:
            str: list of tables in the database.
        """
        logger.debug("Listing tables")

        try:
            _tables = self._run_sql("show tables")
            # logger.debug(f"_tables: {_tables}")
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return f"Error listing tables: {e}"

        return json.dumps(_tables)

    def describe_table(self, table_name: str) -> str:
        """
        Use this function to describe a table.

        Args:
            table_name (str): The table name.

        Returns:
            str: list of tables in the database.
        """
        logger.debug(f"Describing table: {table_name}")

        try:
            _table_description = self._run_sql(f"DESC {table_name}")
        except Exception as e:
            logger.error(f"Error describing table {table_name}: {e}")
            return f"Error describing table {table_name}: {e}"

        return json.dumps(_table_description)

    def run_query(self, query: str, limit: Optional[int] = 10) -> str:
        """
        Use this function to run a presto sql query.

        Args:
            query (str): The query to run.
            limit (int, optional): The limit of the result. Defaults to 10. Use `None` to show all results.

        Returns:
            str: result of the query.
        """
        # logger.debug(f"Running query |\n{query}")

        try:
            return json.dumps(self._run_sql(sql=query, limit=limit))
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return f"Error running query: {e}"
