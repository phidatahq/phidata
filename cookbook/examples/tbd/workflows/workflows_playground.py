"""
1. Install dependencies using: `pip install openai duckduckgo-search sqlalchemy 'fastapi[standard]' newspaper4k lxml_html_clean yfinance agno`
2. Run the script using: `python cookbook/workflows/workflows_playground.py`
"""

from agno.playground import Playground, serve_playground_app
from agno.storage.workflow.sqlite import SqliteWorkflowStorage

# Import the workflows
from blog_post_generator.blog_post_generator import BlogPostGenerator
from game_generator.game_generator import GameGenerator
from investment_report_generator.investment_report_generator import (
    InvestmentReportGenerator,
)
from news_report_generator.news_report_generator import NewsReportGenerator

from cookbook.workflows.startup_idea_validator import StartupIdeaValidator

# Initialize the workflows with SQLite storage

blog_post_generator = BlogPostGenerator(
    workflow_id="generate-blog-post",
    storage=SqliteWorkflowStorage(
        table_name="generate_blog_post_workflows",
        db_file="tmp/workflows.db",
    ),
)
news_report_generator = NewsReportGenerator(
    workflow_id="generate-news-report",
    storage=SqliteWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

investment_report_generator = InvestmentReportGenerator(
    workflow_id="generate-investment-report",
    storage=SqliteWorkflowStorage(
        table_name="investment_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

startup_idea_validator = StartupIdeaValidator(
    workflow_id="validate-startup-idea",
    storage=SqliteWorkflowStorage(
        table_name="validate_startup_ideas_workflow",
        db_file="tmp/workflows.db",
    ),
)

game_generator = GameGenerator(
    workflow_id="game-generator",
    storage=SqliteWorkflowStorage(
        table_name="game_generator_workflows",
        db_file="tmp/workflows.db",
    ),
)

# Initialize the Playground with the workflows
app = Playground(
    workflows=[
        blog_post_generator,
        news_report_generator,
        investment_report_generator,
        game_generator,
        startup_idea_validator,
    ]
).get_app()

if __name__ == "__main__":
    serve_playground_app("workflows_playground:app", reload=True)
