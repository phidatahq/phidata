import os
from datetime import datetime
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from phi.run.response import RunEvent, RunResponse
from phi.tools.linear_tools import LinearTool
from phi.tools.slack import SlackTools
from phi.agent.agent import Agent
from phi.workflow.workflow import Workflow
from phi.storage.workflow.postgres import PgWorkflowStorage
from phi.utils.log import logger


class Task(BaseModel):
    task_title: str = Field(..., description="The title of the task")
    task_description: Optional[str] = Field(None, description="The description of the task")
    task_assignee: Optional[str] = Field(None, description="The assignee of the task")


class LinearIssue(BaseModel):
    issue_title: str = Field(..., description="The title of the issue")
    issue_description: Optional[str] = Field(None, description="The description of the issue")
    issue_assignee: Optional[str] = Field(None, description="The assignee of the issue")
    issue_link: Optional[str] = Field(None, description="The link to the issue")


class LinearIssueList(BaseModel):
    issues: List[LinearIssue] = Field(..., description="A list of issues")


class TaskList(BaseModel):
    tasks: List[Task] = Field(..., description="A list of tasks")


class MeetingAssistantWorkflow(Workflow):
    description: str = "Generate linear tasks and send slack notifications to the team from meeting notes."

    task_agent: Agent = Agent(
        name="Task Agent",
        instructions=["Given a meeting note, generate a list of tasks with titles, descriptions and assignees."],
        response_model=TaskList,
    )

    linear_agent: Agent = Agent(
        name="Linear Agent",
        instructions=["Given a list of tasks, create issues in Linear."],
        tools=[LinearTool()],
        response_model=LinearIssueList,
    )

    slack_agent: Agent = Agent(
        name="Slack Agent",
        instructions=[
            "Send a slack notification to the #test channel with a heading (bold text) including the current date and tasks in the following format: ",
            "*Title*: <issue_title>",
            "*Description*: <issue_description>",
            "*Assignee*: <issue_assignee>",
            "*Issue Link*: <issue_link>",
        ],
        tools=[SlackTools()],
    )

    def run(self, meeting_notes: str, linear_users: Dict[str, str], use_cache: bool = False) -> RunResponse:
        logger.info(f"Generating tasks from meeting notes: {meeting_notes}")

        current_date = datetime.now().strftime("%Y-%m-%d")
        tasks: Optional[TaskList] = None

        if use_cache and "meeting_notes" in self.session_state:
            for cached_tasks in self.session_state["meeting_notes"]:
                if cached_tasks["date"] == current_date:
                    logger.info("Found cached tasks")
                    tasks = cached_tasks["tasks"]
                    break
        else:
            num_tries = 0
            while tasks is None and num_tries < 3:
                num_tries += 1
                try:
                    response: RunResponse = self.task_agent.run(meeting_notes)
                    if response and response.content and isinstance(response.content, TaskList):
                        tasks = response.content
                    else:
                        logger.warning("Invalid response from task agent, trying again...")
                except Exception as e:
                    logger.warning(f"Error generating tasks: {e}")

        if tasks is None or len(tasks.tasks) == 0:
            return RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content="Sorry, could not generate tasks from meeting notes.",
            )

        if "meeting_notes" not in self.session_state:
            self.session_state["meeting_notes"] = []
        self.session_state["meeting_notes"].append({"date": current_date, "tasks": tasks.model_dump_json()})

        project_id = os.getenv("LINEAR_PROJECT_ID")
        team_id = os.getenv("LINEAR_TEAM_ID")
        if project_id is None:
            raise Exception("LINEAR_PROJECT_ID is not set")
        if team_id is None:
            raise Exception("LINEAR_TEAM_ID is not set")

        # Create issues in Linear
        logger.info(f"Creating issues in Linear: {tasks.model_dump_json()}")
        linear_response: RunResponse = self.linear_agent.run(
            f"Create issues in Linear for project {project_id} and team {team_id}: {tasks.model_dump_json()} and here is the dictionary of users and their uuid: {linear_users}. If you fail to create an issue, try again."
        )
        linear_issues = None
        if linear_response:
            logger.info(f"Linear response: {linear_response}")
            linear_issues = linear_response.content

        # Send slack notification with tasks
        if linear_issues:
            logger.info(f"Sending slack notification with tasks: {linear_issues.model_dump_json()}")
            slack_response: RunResponse = self.slack_agent.run(linear_issues.model_dump_json())
            logger.info(f"Slack response: {slack_response}")

        return slack_response


# Create the workflow
meeting_assistant = MeetingAssistantWorkflow(
    session_id="meeting-assistant",
    storage=PgWorkflowStorage(
        table_name="meeting_assistant_workflows",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

meeting_notes = open(
    "/Users/manthangupta/Desktop/lab/phidata/cookbook/examples/meeting_assistant/meeting_notes.txt", "r"
).read()
users_uuid = {
    "Sarah": "8d4e1c9a-b5f2-4e3d-9a76-f12d8e3b4c5a",
    "Mike": "2f9b7d6c-e4a3-42f1-b890-1c5d4e8f9a3b",
    "Emma": "7a1b3c5d-9e8f-4d2c-a6b7-8c9d0e1f2a3b",
    "Alex": "4c5d6e7f-8a9b-0c1d-2e3f-4a5b6c7d8e9f",
    "James": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
}

# Run workflow
meeting_assistant.run(meeting_notes=meeting_notes, linear_users=users_uuid)
