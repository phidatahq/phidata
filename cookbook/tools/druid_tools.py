from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.druiddb import DruidTools
from phi.model.openai import OpenAIChat

llm = Ollama(id="llama3.1", host="http://localhost:11434")

druid_tools = DruidTools(
    host="3.91.253.36",
    port=8888,
    list_tables=True,
    describe_table=True,
    run_query=True,
    table_sample=True,
    table_stats=True,
)

agent = Agent(
    name="druid_analyst",
    # provider=llm,
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[druid_tools],
    description="I am a expert druid data analyst that helps you analyze data in Druid databases. I execute queries and provide accurate results without making assumptions.",
    instructions=[
        "NEVER make up or hallucinate data - if a query fails, explain the error clearly",
        "NEVER show example/fake data - only show actual query results",
        "ONLY use database tools when explicitly asked for database information",
        "For greetings or general questions, respond naturally WITHOUT using any tools",
        "Use list_tables when: User asks to see/list/show tables",
        "Use table_sample when: User asks for data samples",
        "Use table_stats when: User asks for table statistics",
        "Use table_sample when: User asks for analysis from some table. use this function to check the data and provide analysis or write queries for analysis.",
        "Use run_query when: user want to do analysis or asks for something perticular from druid database. Create query, run it and then show the answers. "
        "When showing results:",
        "1. Show the tool being called",
        "2. Show the actual results or error message",
        "3. Explain what the results mean",
        "4. If there's an error, explain what went wrong",
        "When a tool call fails:",
        "1. Show the exact error message",
        "2. Explain what the error means in simple terms",
        "3. Suggest valid alternatives if possible",
        "4. NEVER make up fake results or examples",
    ],
    markdown=True,
    show_tool_calls=True,
    debug_mode=True,
)

agent.cli_app(markdown=True)
