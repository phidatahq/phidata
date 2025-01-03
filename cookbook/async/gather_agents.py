import asyncio
from rich.pretty import pprint
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

providers = ["openai", "anthropic", "ollama", "cohere", "google"]
instructions = [
    "Your task is to write a well researched report on AI providers.",
    "The report should be unbiased and factual.",
]


async def get_reports():
    tasks = []
    for provider in providers:
        agent = Agent(
            model=OpenAIChat(id="gpt-4"),
            instructions=instructions,
            tools=[DuckDuckGo()],
        )
        tasks.append(agent.arun(f"Write a report on the following AI provider: {provider}"))

    results = await asyncio.gather(*tasks)
    return results


async def main():
    results = await get_reports()
    for result in results:
        print("************")
        pprint(result.content)
        print("************")
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
