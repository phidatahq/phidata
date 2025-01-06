from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.github import GithubTools
from phi.tools.write_to_local_tools import WriteToLocal

readme_gen_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    name="Readme Generator Agent",
    tools=[GithubTools(), WriteToLocal()],
    markdown=True,
    debug_mode=True,
    instructions=[
        "You are readme generator agent",
        "You'll be given repository url or repository name from user."
        "You'll use the `get_repository` tool to get the repository details."
        "You have to pass the repo_name as argument to the tool. It should be in the format of owner/repo_name. If given url extract owner/repo_name from it."
        "Also call the `get_repository_languages` tool to get the languages used in the repository."
        "You are an AI assistant that can write Readme files for open-source GitHub projects."
        "Return your response in markdown format. You will be provided with languages used is project, the repo URL, clone URL etc.Give an good response with like how to clone the project and install the dependency , run the project etc. Also give icons like of mit license , size of repo etc. "
        "Ignore the lines code in each language but include the languages in other sections with their icons",
        "You have to write the readme file in the current directory",
    ],
)

readme_gen_agent.print_response("Get details of https://github.com/phidatahq/phidata", markdown=True)
