"""Configure Product Manager and exercise its bounded tools without a model call.

Prerequisites: Install agno, sqlalchemy, openai and fastmcp.
Run: .venv/bin/python cookbook/05_agent_os/30_company/05_product_manager.py
Try: With provider credentials, call agent_os.product_manager.print_response(...).
     Add manager=OSManager() to compose Product Manager as an OS Manager member.
"""

import json
from tempfile import TemporaryDirectory

from agno.company import CompanyManager
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, CompanyConfig, MCPConfig
from agno.registry import Registry
from agno.run import RunContext
from agno.tools.company import CompanyTools

if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        db = SqliteDb(db_file=directory + "/company.db")
        tools = CompanyTools(db, user_isolation=True)
        agent_os = AgentOS(
            db=db,
            registry=Registry(models=[OpenAIResponses(id="gpt-5.6-luna")]),
            company=CompanyConfig(),
            user_isolation=True,
            mcp=MCPConfig(tools=[tools]),
            telemetry=False,
        )
        manager = CompanyManager(db)
        product = manager.create(
            "SDK", purpose="Build reliable agents", user_id="alice"
        )
        # Trusted application code supplies context. HTTP and MCP inject their
        # authenticated caller automatically; identity is never a model argument.
        context = RunContext(run_id="demo", session_id="planning", user_id="alice")
        proposal = json.loads(
            tools.propose_company_task(
                product["id"],
                "Draft release notes",
                brief="Summarize reviewed changes",
                _agno_run_context=context,
            )
        )
        assert proposal["status"] == "backlog" and proposal["user_id"] == "alice"
        tools.update_company_status(
            product["id"],
            "# Status\n\nRelease notes proposed.\n",
            1,
            _agno_run_context=context,
        )
        tools.log_company_decision(
            "Review release notes before publishing",
            reasoning="Human approval required",
            _agno_run_context=context,
        )
        assert agent_os.product_manager is not None
        assert agent_os.product_manager not in agent_os.registry.agents
        assert not any(
            "transition" in name or "schedule" in name for name in tools.functions
        )
        db.close()
        print("Product Manager configured; Backlog proposal, status and decision saved")
        print("No model call was made")
