import json
from typing import List, Optional, Dict, Any, Union

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from sqlalchemy import create_engine, Engine, Row
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.sql.expression import text
except ImportError:
    raise ImportError("`sqlalchemy` not installed")


class SQLToolkit(Toolkit):
    def __init__(
        self,
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        schema: Optional[str] = None,
        dialect: Optional[str] = None,
        tables: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name="sql_toolkit")

        # Get the database engine
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)
        elif user and password and host and port and dialect:
            if schema is not None:
                _engine = create_engine(f"{dialect}://{user}:{password}@{host}:{port}/{schema}")
            else:
                _engine = create_engine(f"{dialect}://{user}:{password}@{host}:{port}")

        if _engine is None:
            raise ValueError("Could not build the database connection")

        # Database connection
        self.db_engine: Engine = _engine
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Tables this toolkit can access
        self.tables: Optional[Dict[str, Any]] = tables

        # Register functions in the toolkit
        self.register(self.get_table_list)
        self.register(self.run_sql_query)

    def _run_sql(self, sql: str, limit: Optional[int] = None) -> Optional[Union[List, Dict]]:
        """Internal function to run a sql query.

        Args:
            sql (str): The sql query to run.
            limit (int, optional): The number of rows to return. Defaults to None.

        Returns:
            List[dict]: The result of the query.
        """
        logger.debug(f"Running sql |\n{sql}")

        with self.Session.begin() as session:
            if limit is None:
                sql_result = session.execute(text(sql)).fetchall()
            else:
                sql_result = session.execute(text(sql)).fetchmany(limit)

        logger.debug(f"SQL result: {sql_result}")
        if sql_result is None:
            return None
        elif isinstance(sql_result, list):
            return [row._asdict() for row in sql_result]
        elif isinstance(sql_result, Row):
            return sql_result._asdict()
        else:
            logger.debug(f"SQL result type: {type(sql_result)}")
            return None

    def get_table_list(self) -> str:
        """
        Use this function to get a list of tables you have access to.

        Returns:
            str: list of tables in the database.
        """
        if self.tables is not None:
            return json.dumps(self.tables)

        try:
            _tables = self._run_sql("show tables;")
            logger.debug(f"_tables: {_tables}")
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return f"Error getting tables: {e}"

        return json.dumps(_tables)

    def run_sql_query(self, query: str, limit: Optional[int] = 10) -> str:
        """
        Use this function to run a SQL query.

        Args:
            query (str): The query to run.
            limit (int, optional): The number of rows to return. Defaults to 10. Use `None` to show all results.

        Returns:
            str: Result of the SQL query.
        """
        try:
            return json.dumps(self._run_sql(sql=query, limit=limit))
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return f"Error running query: {e}"
