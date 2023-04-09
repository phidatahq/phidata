import time
from typing import Any
from phidata.utils.log import logger

try:
    from langchain.tools import BaseTool
except ImportError:
    logger.warning("Langchain not available.")
    raise

from phidata.llm.duckdb.query import run_duckdb_query


class DuckDBQueryTool(BaseTool):
    name: str = "execute"
    description: str = """Useful for when you need to run SQL queries against a DuckDB database.
    Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    duckdb_connection: Any = None

    def _run(self, query: str) -> str:
        """Use the tool to run a query against the database."""
        query_result = run_duckdb_query(self.duckdb_connection, query)
        time.sleep(1)
        return query_result

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("Not supported")
