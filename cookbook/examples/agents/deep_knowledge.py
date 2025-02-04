"""🤔 DeepKnowledge - An AI Agent that iteratively searches a knowledge base to answer questions

This agent performs iterative searches through its knowledge base, breaking down complex
queries into sub-questions, and synthesizing comprehensive answers. It's designed to explore
topics deeply and thoroughly by following chains of reasoning.

In this example, the agent uses the Agno documentation as a knowledge base and
DuckDuckGo to answer questions from the internet.

Key Features:
- Uses both internal knowledge base and web search
- Iterative search refinement
- Source attribution and citations

Run `pip install openai lancedb tantivy duckduckgo-search inquirer agno` to install dependencies.
"""

from textwrap import dedent

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.url import UrlKnowledge
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.utils.pprint import pprint_run_response
from agno.vectordb.lancedb import LanceDb, SearchType

# Initialize the knowledge base with your preferred documentation or knowledge source
# Here we use Agno docs as an example, but you can replace with any relevant URLs
knowledge = UrlKnowledge(
    urls=["https://docs.agno.com/llms-full.txt"],
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="knowledge_base",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
# Load the knowledge base (comment out after first run)
# knowledge.load()

# Create the DeepKnowledge agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description=dedent("""\
    You are DeepKnowledge, an advanced reasoning agent designed to provide thorough,
    well-researched answers to any query by searching your knowledge base and the web.

    Your strengths include:
    - Breaking down complex topics into manageable components
    - Connecting information across multiple domains
    - Providing nuanced, well-researched answers
    - Maintaining intellectual honesty and citing sources
    - Explaining complex concepts in clear, accessible terms"""),
    instructions=dedent("""\
    Your mission is to leave no stone unturned in your pursuit of the correct answer.

    To achieve this, follow these steps:
    1. **Analyze the question and break it down into key components**. You MUST identify at least 3-5 key components to search for.
    2. **Initial Search:** Searching your knowledge base for relevant information. You must make multiple search queries to get all relevant information.
    3. **Evaluation:** If the answer from the knowledge base is incomplete, ambiguous, or insufficient,
        do not settle. Instead, proceed to conduct a web search to gather additional context and data.
    4. **Iterative Process:**
        - Continue alternating between your knowledge base and web searches.
        - Reevaluate the completeness of your answer after each search iteration.
        - Repeat the search process until you are confident that every aspect of the question is addressed.
    4. **Reasoning Documentation:** Clearly document your reasoning process:
        - Note when additional searches were triggered.
        - Indicate which pieces of information came from the knowledge base versus web sources.
        - Explain how you reconciled any conflicting or ambiguous information.
    5. **Final Synthesis:** Only finalize and present your answer once you have verified it through multiple search passes.
        Include all pertinent details and provide proper references for both internal and web-sourced data.
    6. **Continuous Improvement:** If new, relevant information emerges even after presenting your answer,
        be prepared to update or expand upon your response.

    **Communication Style:**
    - Use clear and concise language.
    - Organize your response with numbered steps, bullet points, or short paragraphs as needed.
    - Be transparent about your search process and cite your sources.
    - Ensure that your final answer is comprehensive and leaves no part of the query unaddressed.

    Remember: **Do not finalize your answer until every angle of the question has been explored.**"""),
    knowledge=knowledge,
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)

# Run the agent if the script is executed directly
if __name__ == "__main__":
    import inquirer

    # Example Agno-related questions
    example_topics = [
        "What are AI agents and how do they work in Agno?",
        "What chunking strategies does Agno support for text processing?",
        "Which vector databases can I use with Agno?",
        "How does knowledge retrieval work in Agno?",
        "What types of embeddings does Agno support?",
    ]

    # Create choices including numbered topics and custom option
    choices = [f"{i + 1}. {topic}" for i, topic in enumerate(example_topics)]
    choices.append("Enter custom question...")

    # Create and show the selection prompt
    questions = [
        inquirer.List(
            "topic",
            message="Select a topic or ask a different question:",
            choices=choices,
        )
    ]
    answer = inquirer.prompt(questions)

    # Handle custom input or selection
    if answer["topic"] == "Enter question...":
        questions = [
            inquirer.Text(
                "custom",
                message="Enter your question:",
                default="What are AI agents and how do they work in Agno?",
            )
        ]
        custom_answer = inquirer.prompt(questions)
        topic = custom_answer["custom"]
    else:
        # Extract the actual topic from the numbered choice
        topic = example_topics[int(answer["topic"].split(".")[0]) - 1]

    # Print the response
    pprint_run_response(agent.run(topic, stream=True), markdown=True)

# Example prompts to try:
"""
Explore Agno's capabilities with these queries:
1. "What are the different types of agents in Agno?"
2. "How does Agno handle knowledge base management?"
3. "What embedding models does Agno support?"
4. "How can I implement custom tools in Agno?"
5. "What storage options are available for workflow caching?"
6. "How does Agno handle streaming responses?"
7. "What types of LLM providers does Agno support?"
8. "How can I implement custom knowledge sources?"
"""
