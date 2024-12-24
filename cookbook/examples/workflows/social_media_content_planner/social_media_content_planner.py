from phi.agent import Agent, RunResponse
from phi.workflow import Workflow
from phi.model.openai import OpenAIChat
from phi.tools.firecrawl import FirecrawlTools
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from dotenv import load_dotenv
import scheduler
from prompts import agents_config, tasks_config
from config import BlogPostURL, PostType

# Load environment variables
load_dotenv()


# Define Pydantic models to structure responses
class BlogAnalyzer(BaseModel):
    """
    Represents the response from the Blog Analyzer agent.
    Includes the blog title and content in Markdown format.
    """
    title: str
    blog_content_markdown: str


class Tweet(BaseModel):
    """
    Represents an individual tweet within a Twitter thread.
    """
    content: str
    is_hook: bool = False  # Marks if this tweet is the "hook" (first tweet)
    media_urls: Optional[List[str]] = []  # Associated media URLs, if any


class Thread(BaseModel):
    """
    Represents a complete Twitter thread containing multiple tweets.
    """
    topic: str
    tweets: List[Tweet]


class LinkedInPost(BaseModel):
    """
    Represents a LinkedIn post.
    """
    content: str
    media_url: Optional[str] = None  # Optional media attachment URL


class ContentPlanningWorkflow(Workflow):
    """
    This workflow automates the process of:
    1. Scraping a blog post using the Blog Analyzer agent.
    2. Generating a content plan for either Twitter or LinkedIn based on the scraped content.
    3. Scheduling and publishing the planned content.
    """
    # This description is used only in workflow UI
    description: str = "Plan, schedule, and publish social media content based on a blog post."

    # Blog Analyzer Agent: Extracts blog content (title, sections) and converts it into Markdown format for further use.
    blog_analyzer = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[FirecrawlTools(scrape=True, crawl=False)],  # Enables blog scraping capabilities
        description=f"{agents_config['blog_analyzer']['role']} - {agents_config['blog_analyzer']['goal']}",
        instructions=[
            f"{agents_config['blog_analyzer']['backstory']}",
            tasks_config['analyze_blog']['description'],  # Task-specific instructions for blog analysis
        ],
        response_model=BlogAnalyzer,  # Expects response to follow the BlogAnalyzer Pydantic model
    )

    # Twitter Thread Planner: Creates a Twitter thread from the blog content, each tweet is concise, engaging,
    # and logically connected with relevant media.
    twitter_thread_planner = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description=f"{agents_config['twitter_thread_planner']['role']} - {agents_config['twitter_thread_planner']['goal']}",
        instructions=[
            f"{agents_config['twitter_thread_planner']['backstory']}",
            tasks_config['create_twitter_thread_plan']['description'],
        ],
        response_model=Thread,  # Expects response to follow the Thread Pydantic model
    )

    # LinkedIn Post Planner: Converts blog content into a structured LinkedIn post, optimized for a professional
    # audience with relevant hashtags.
    linkedin_post_planner = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description=f"{agents_config['linkedin_post_planner']['role']} - {agents_config['linkedin_post_planner']['goal']}",
        instructions=[
            f"{agents_config['linkedin_post_planner']['backstory']}",
            tasks_config['create_linkedin_post_plan']['description'],
        ],
        response_model=LinkedInPost,  # Expects response to follow the LinkedInPost Pydantic model
    )

    def scrape_blog_post(self, blog_post_url: str):
        response: RunResponse = self.blog_analyzer.run(blog_post_url)
        if response.content_type == "BlogAnalyzer":
            result = response.content
            print(f"Blog title: {result.title}")
            return result.blog_content_markdown
        else:
            raise ValueError("Unexpected content type received from blog analyzer.")

    def generate_plan(self, blog_content: str, post_type: str) -> dict:
        if post_type == "twitter":
            print(f"Generating post plan for {post_type}")
            plan_response: RunResponse = self.twitter_thread_planner.run(blog_content)
        elif post_type == "linkedin":
            print(f"Generating post plan for {post_type}")
            plan_response: RunResponse = self.linkedin_post_planner.run(blog_content)
        else:
            raise ValueError(f"Unsupported post type: {post_type}")

        if plan_response.content_type == "Thread" or plan_response.content_type == LinkedInPost:
            return plan_response.content
        elif plan_response.content_type == "application/json":
            data = json.loads(plan_response.content)
            if post_type == "twitter":
                return Thread(**data)
            else:
                return LinkedInPost(**data)
        else:
            raise ValueError("Unexpected content type received from planner.")

    def schedule_and_publish(self, plan, post_type: str):
        """
        Schedules and publishes the content leveraging Typefully api.
        """
        print(f"# Publishing content for post type: {post_type}")

        # Use the `scheduler` module directly to schedule the content
        response = scheduler.schedule(
            thread_model=plan,
            post_type=post_type,  # Either "twitter" or "linkedin"
        )

        if response:
            print(f"# Content scheduled successfully! Share URL: {response.get('share_url')}")
        else:
            print("# Failed to schedule content.")

    def run(self, blog_post_url, post_type):
        """
        Args:
            blog_post_url: URL of the blog post to analyze.
            post_type: Type of post to generate (e.g., twitter or linkedin).
        """
        # Scrape the blog post
        blog_content = self.scrape_blog_post(self.blog_post_url)

        # Generate the plan based on the blog and post type
        plan = self.generate_plan(blog_content, self.post_type)

        # Schedule and publish the content
        self.schedule_and_publish(plan, self.post_type)


if __name__ == "__main__":
    # Initialize and run the workflow
    blogpost_url = "https://blog.dailydoseofds.com/p/5-chunking-strategies-for-rag"
    workflow = ContentPlanningWorkflow()
    workflow.run(blog_post_url=blogpost_url, post_type=PostType.TWITTER)

