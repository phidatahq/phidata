import textwrap
from phidata.utils.log import logger

try:
    import duckdb
except ImportError:
    logger.warning("DuckDB not available.")
    raise

try:
    from langchain import LLMMathChain, SerpAPIWrapper
    from langchain.agents import Tool, initialize_agent
    from langchain.llms import OpenAIChat
except ImportError:
    logger.warning("Langchain not available.")
    raise

from phidata.llm.duckdb.chain import get_duckdb_query_chain
from phidata.llm.duckdb.query import run_duckdb_query, describe_table_or_view


def create_duckdb_agent(
    duckdb_connection: duckdb.DuckDBPyConnection, model_name: str = "gpt-3.5-turbo"
):
    """
    Agents use an LLM to determine which actions to take and in what order.
    An action can either be using a tool and observing its output, or returning to the user.

    This function creates an agent that can answer questions about a duckdb database.
    """

    # Step 1: Load the LLM to control the agent.
    llm = OpenAIChat(model_name=model_name, temperature=0)  # type: ignore

    # Step 2: Load tools that the agent can use to answer questions.
    llm_math_chain = LLMMathChain(llm=llm, verbose=True)
    db_op_chain = get_duckdb_query_chain(llm=llm, duckdb_connection=duckdb_connection)
    tools = [
        Tool(
            name="Calculator",
            func=llm_math_chain.run,
            description="Useful for when you need to answer questions about math",
        ),
        Tool(
            name="Show Tables",
            func=lambda _: run_duckdb_query(duckdb_connection, "show tables;"),
            description="Useful to show the available tables and views. Empty input required.",
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(duckdb_connection, table),
            description="Useful to show the column names and types of a table or view. Use the table name as the input.",  # noqa: E501
        ),
        Tool(
            name="Data Op",
            func=lambda input: db_op_chain(
                {
                    "table_names": lambda _: run_duckdb_query(
                        duckdb_connection, "show tables;"
                    ),
                    "input": input,
                }
            ),
            description=textwrap.dedent(
                """useful for when you need to operate on data and answer questions by querying for data.
            Input should be in the form of a natural language question containing full context
            including what tables and columns are relevant to the question. Use only after data is present and loaded.
            """,  # noqa: E501
            ),
        ),
    ]

    # Step 2: Initialize the agent
    agent = initialize_agent(
        tools,
        llm,
        agent="zero-shot-react-description",  # type: ignore
        agent_kwargs={
            "input_variables": ["input", "agent_scratchpad", "table_names"],
            "prefix": prompt_prefix,
            "suffix": prompt_suffix,
        },
        # return_intermediate_steps=True,
        verbose=True,
    )
    return agent


prompt_prefix = """Answer the following question as best you can by querying for data to back up
your answer. Even if you know the answer, you MUST show you can get the answer from the database.

Refuse to delete any data, or drop tables. When answering, you MUST query the database for any data.
Check the available tables exist first. Prefer to take single independent actions. Prefer to create views
of data as one action, then select data from the view.

Always share the SQL queries you use to get the answer.

It is important that you use the exact phrase "Final Answer: " in your final answer.
List all SQL queries returned by Data Op in your final answer.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.

You have access to the following data tables:
{table_names}

Only use the below tools. You have access to the following tools:
"""

prompt_suffix = """
It is important that you use the exact phrase "Final Answer: <Summary>" in your final answer.

Begin! Remember to share the SQL queries you use to get the answer.

Question: {input}
Thought: I should look at the tables in the database to see what I can query.
{agent_scratchpad}"""
