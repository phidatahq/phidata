"""Execute an accepted Task through the durable queue without a model call.

Prerequisites: Install agno, sqlalchemy, psycopg, fastapi and httpx; start PostgreSQL.
Run: .venv/bin/python cookbook/05_agent_os/30_company/06_execute_tasks.py
Try: Set COMPANY_DB=postgres to store Company records and runs in PostgreSQL too.
"""

import json
import os
import time
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.job_queue import QueueConfig
from agno.os import AgentOS, CompanyConfig
from agno.registry import Registry
from agno.workflow import Step, StepInput, StepOutput, Workflow
from fastapi.testclient import TestClient
from sqlalchemy import text


def draft(step_input: StepInput) -> StepOutput:
    context = json.loads(step_input.input)
    assert set(context) == {"brief", "wiki", "evidence"}
    return StepOutput(content="Draft ready for review: " + context["brief"])


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        schema = "company_cookbook_" + uuid4().hex
        queue_db = PostgresDb(
            db_url=os.getenv(
                "COMPANY_QUEUE_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
            ),
            db_schema=schema,
        )
        db = (
            queue_db
            if os.getenv("COMPANY_DB") == "postgres"
            else SqliteDb(db_file=directory + "/company.db")
        )
        workflow = Workflow(
            id="draft",
            db=db,
            steps=[Step(name="Draft", executor=draft)],
            telemetry=False,
        )
        agent_os = AgentOS(
            db=db,
            registry=Registry(workflows=[workflow]),
            company=CompanyConfig(),
            queue=QueueConfig(durable=True, db=queue_db, poll_interval=0.1),
            telemetry=False,
        )
        try:
            with TestClient(agent_os.get_app()) as client:
                product = client.post("/company/products", json={"name": "SDK"}).json()
                task = client.post(
                    "/company/tasks",
                    json={
                        "product_id": product["id"],
                        "title": "Draft release notes",
                        "brief": "Summarize reviewed changes",
                        "evidence": [{"reference": "Reviewed release changes"}],
                    },
                ).json()
                path = "/company/tasks/" + task["id"]
                accepted = client.post(
                    path + "/transitions",
                    json={
                        "target": "ready",
                        "reason": "Scope agreed",
                        "executor_type": "workflow",
                        "executor_id": "draft",
                    },
                )
                assert accepted.status_code == 200, accepted.text
                started = client.post(path + "/runs", json={"attempt": 1})
                assert started.status_code == 202, started.text
                duplicate = client.post(path + "/runs", json={"attempt": 1})
                assert duplicate.json()["run_id"] == started.json()["run_id"]
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    task = client.get(path).json()
                    if task["status"] == "in_review":
                        break
                    time.sleep(0.1)
                assert task["status"] == "in_review", task
                assert task["result"]["status"] == "COMPLETED"
                history = client.get(
                    path + "/runs", params={"limit": 10, "page": 1}
                ).json()
                assert history["meta"]["total_count"] == 1
                attention = client.get(
                    "/company/attention", params={"product_id": product["id"]}
                ).json()
                print("Task completed and awaits review")
                print(json.dumps(attention, indent=2))
                print("Duplicate start returned the first run; no model call was made")
        finally:
            if db is not queue_db:
                db.close()
            with queue_db.db_engine.begin() as connection:
                connection.execute(
                    text('DROP SCHEMA IF EXISTS "' + schema + '" CASCADE')
                )
            queue_db.close()
