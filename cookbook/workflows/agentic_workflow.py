from cookbook.workflows.blog_post_generator import BlogPostGenerator
from phi.agent.agent import Agent

agent = Agent(
    name="Agentic Workflow",
    workflows=[BlogPostGenerator()],
    debug_mode=True,
)

agent.print_response("Write a blog post on the topic of AI and the future of work")
