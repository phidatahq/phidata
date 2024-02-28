from os import getenv
import json
from typing import List, Optional

from phi.tools import Toolkit
from phi.utils.log import logger
from phi.docker.app.postgres import PostgresDb

try:
    from sqlalchemy import create_engine
    from sqlalchemy.schema import Table, MetaData
    from sqlalchemy.sql.expression import select, text
except ImportError:
    raise ImportError("`sqlalchemy` not installed. Please install using `pip install sqlalchemy`.")


class SQLAlchemyToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="sqlalchemy_tools")

        assistant_user: str = getenv("ASSISTANT_USER") or "phi"
        assistant_host: str = "localhost"
        assistant_password: str = getenv("ASSISTANT_PASSWORD") or "phi"
        assistant_port: int = 5555
        assistant_catalog: str = getenv("ASSISTANT_CATALOG") or "phi"
        assistant_schema: str = getenv("ASSISTANT_SCHEMA") or "phi"

        self.connection_string = (
            f"postgresql+psycopg://{assistant_user}:{assistant_password}@{assistant_host}:{assistant_port}/{assistant_schema}"
        )
        logger.debug(f"self.connection_string: {self.connection_string}")
        self.engine = create_engine(self.connection_string)
        self.connection = self.engine.connect()
        # self.register(self.list_tables)
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
        # logger.debug(f"Listing tables |")

        try:
            _tables = self._run_sql("show tables")
            # logger.debug(f"_tables: {_tables}")
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return f"Error listing tables: {e}"

        return json.dumps(_tables)

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
