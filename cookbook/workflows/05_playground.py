"""
1. Install dependencies using: `pip install openai duckduckgo-search sqlalchemy 'fastapi[standard]' newspaper4k lxml_html_clean yfinance phidata`
2. Run the script using: `python cookbook/workflows/05_playground.py`
"""

from cookbook.workflows.game_generator import GameGenerator
from phi.playground import Playground, serve_playground_app
from phi.storage.workflow.sqlite import SqlWorkflowStorage

# Import the workflows
from blog_post_generator import BlogPostGenerator  # type: ignore
from news_report_generator import NewsReportGenerator  # type: ignore
from investment_report_generator import InvestmentReportGenerator  # type: ignore

# Initialize the workflows with SQLite storage

blog_post_generator = BlogPostGenerator(
    workflow_id="generate-blog-post",
    storage=SqlWorkflowStorage(
        table_name="generate_blog_post_workflows",
        db_file="tmp/workflows.db",
    ),
)
news_report_generator = NewsReportGenerator(
    workflow_id="generate-news-report",
    storage=SqlWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)
investment_report_generator = InvestmentReportGenerator(
    workflow_id="generate-investment-report",
    storage=SqlWorkflowStorage(
        table_name="investment_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

game_generator = GameGenerator(
    workflow_id="game-generator",
    storage=SqlWorkflowStorage(
        table_name="game_generator_workflows",
        db_file="tmp/workflows.db",
    ),
)

# Initialize the Playground with the workflows
app = Playground(workflows=[blog_post_generator, news_report_generator, investment_report_generator]).get_app()

if __name__ == "__main__":
    serve_playground_app("05_playground:app", reload=True)
