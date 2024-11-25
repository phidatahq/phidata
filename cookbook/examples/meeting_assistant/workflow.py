
from phi.run.response import RunEvent, RunResponse
from phi.storage.workflow.postgres import PgWorkflowStorage
from phi.tools.slack import SlackTools
from pydantic import BaseModel, Field
from typing import List, Optional
from phi.agent.agent import Agent
from phi.workflow.workflow import Workflow
from phi.utils.log import logger
import os
from datetime import datetime

class Task(BaseModel):
    task_title: str = Field(..., description="The title of the task")
    task_description: Optional[str] = Field(None, description="The description of the task")
    task_assignee: Optional[str] = Field(None, description="The assignee of the task")

class TaskList(BaseModel):
    tasks: List[Task] = Field(..., description="A list of tasks")


class MeetingAssistantWorkflow(Workflow):
    description: str = "Generate linear tasks and send slack notifications to the team from meeting notes."

    task_agent: Agent = Agent(
        name="Task Agent",
        instructions=["Given a meeting note, generate a list of tasks with titles, descriptions and assignees."],
        response_model=TaskList,
    )

    slack_agent: Agent = Agent(
        name="Slack Agent",
        instructions=[
            "Send a slack notification to the #test channel with a heading (bold text) including the current date and tasks in the following format: ",
            "*Title*: <task_title>",
            "*Description*: <task_description>",
            "*Assignee*: <task_assignee>",
        ],
        tools=[SlackTools(token=os.getenv("SLACK_TOKEN"))],
    )

    def run(self, meeting_notes: str, use_cache: bool = False) -> RunResponse:
        logger.info(f"Generating tasks from meeting notes: {meeting_notes}")

        current_date = datetime.now().strftime("%Y-%m-%d")

        if use_cache and "meeting_notes" in self.session_state:
            for cached_tasks in self.session_state["meeting_notes"]:
                if cached_tasks["date"] == current_date:
                    logger.info("Found cached tasks")
                    return RunResponse(run_id=self.run_id, event=RunEvent.workflow_completed, content=cached_tasks["tasks"])

        tasks: Optional[TaskList] = None
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

        # Send slack notification with tasks
        logger.info(f"Sending slack notification with tasks: {tasks.model_dump_json()}")
        slack_response: RunResponse = self.slack_agent.run(tasks.model_dump_json())
        logger.info(f"Slack response: {slack_response}")

        return slack_response


# Create the workflow
meeting_assistant = MeetingAssistantWorkflow(
    session_id=f"meeting-assistant",
    storage=PgWorkflowStorage(
        table_name="meeting_assistant_workflows",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

meeting_notes = open("/Users/manthangupta/Desktop/lab/phidata/cookbook/examples/meeting_assistant/meeting_notes.txt", "r").read()

# Run workflow
meeting_assistant.run(meeting_notes=meeting_notes)
