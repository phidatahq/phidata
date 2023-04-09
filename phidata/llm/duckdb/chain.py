from phidata.utils.log import logger

try:
    from langchain import LLMChain
    from langchain.agents import AgentExecutor, Tool, ZeroShotAgent
except ImportError:
    logger.warning("Langchain not available.")
    raise

from phidata.llm.duckdb.tool import DuckDBQueryTool
from phidata.llm.duckdb.query import run_duckdb_query, describe_table_or_view


def get_duckdb_query_chain(llm, duckdb_connection):
    tools = [
        Tool(
            name="Show Tables",
            func=lambda _: run_duckdb_query(duckdb_connection, "show tables;"),
            description="Useful to show the available tables and views. Empty input required.",
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(duckdb_connection, table),
            description="Useful to show the column names and types of a table or view. Use a valid table name as the input.",  # noqa: E501
        ),
        Tool(
            name="Query Inspector",
            func=lambda query: query.strip('"').strip("'"),
            description="Useful to show the query before execution. Always inspect your query before execution. Input MUST be on one line.",  # noqa: E501
        ),
        DuckDBQueryTool(duckdb_connection=duckdb_connection),
    ]

    # https://langchain.readthedocs.io/en/latest/modules/agents/examples/custom_agent.html#custom-llmchain
    prompt = ZeroShotAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=suffix,
        input_variables=["input", "agent_scratchpad", "table_names"],
    )

    llm_chain = LLMChain(llm=llm, prompt=prompt)

    tool_names = [tool.name for tool in tools]

    agent = ZeroShotAgent(
        llm_chain=llm_chain,
        allowed_tools=tool_names,
    )
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
    )

    return agent_executor


prefix = """Given an input question, identify the relevant tables and relevant columns, then create
one single syntactically correct DuckDB query to inspect, then execute, before returning the answer.
If the input is a valid looking SQL query selecting data or creating a view, execute it directly.

Even if you know the answer, you MUST show you can get the answer from the database.
Inspect your query before execution.

Always share the SQL queries you use to get the answer.

Refuse to delete any data, or drop tables. You only execute one statement at a time. You may import data.

Example imports:
- CREATE table customers AS SELECT * FROM 'data/records.json';
- CREATE VIEW covid AS SELECT * FROM 's3://covid19-lake/data.csv';

Unless the user specifies in their question a specific number of examples to obtain, limit your
query to at most 5 results. You can order the results by a relevant column to return the most interesting
examples in the database.

Pay attention to use only the column names that you can see in the schema description. Pay attention
to which column is in which table.

You have access to the following tables/views:
{table_names}

You have access to the following tools:
"""

suffix = """After outputting the Action Input you never output an Observation, that will be provided to you.

Always ist the relevant SQL queries you ran in your final answer.

If a query fails, try fix it, if the database doesn't contain the answer, or returns no results,
output a summary of your actions in your final answer. It is important that you use the exact format:

Final Answer: I have successfully created a view of the data.

Queries should be output on one line and don't use any escape characters.

Let's go! Remember it is important that you use the exact phrase "Final Answer: " to begin your
final answer.

Question: {input}
Thought: I should describe the most relevant tables in the database to see what columns will be useful.
{agent_scratchpad}"""
