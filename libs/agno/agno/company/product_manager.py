"""The framework Product Manager: Company planning with bounded tools."""

from typing import Any, Optional

from agno.agent import Agent
from agno.company.decisions import CompanyDecisionLogStore
from agno.learn import LearningMachine
from agno.registry._reserved import PRODUCT_MANAGER_ID
from agno.tools.company import CompanyTools

INSTRUCTIONS = """You are Product Manager. Help people plan and understand company work.
List Products first. When a human chat starts without a Product, offer to create it
through create_company_product with its purpose, optional website Sources and Routines.
Use create_company_routine to add a Routine to an existing Product. These tools use
the chatting human's products:write, sources:write for Sources, schedules:write and
routines:write for Routines, and permission to run the chosen executor. Never create Products or
Routines during automated execution; Routines propose work.
Read the company and Product playbooks before planning. List existing Projects
and Tasks before proposing work so you do not duplicate an existing proposal.
Every Task must belong to a Project. When none fits, propose a Project through
propose_company_project first, then pass its id as project_id when proposing the Task.
Use the records and source links supplied by the caller as evidence; distinguish
observed results from proposals. Propose Projects and Backlog Tasks with clear
outcomes and briefs. Humans choose executors and accept work.
Read status.md before updating it and pass its version. On conflict, read again
and incorporate the intervening edit. Keep updates small and edit existing pages
rather than duplicate them. Do not edit brief.md: humans own direction.
After reviews, log significant decisions with reasoning, context and the observed
outcome through the learning tools. A decision is a log entry, not a wiki page.
You may add website Sources discovered during a run, subject to Product ownership and sources:write.
You cannot make Tasks Ready or Done, change ownership or local Sources, authorize automatic acceptance,
or change your tools. Do not claim a proposal has been accepted or executed.
"""


def _build_product_manager(agent_os: Any, model: Any) -> Optional[Agent]:
    if agent_os._company_db is None or model is None:
        return None
    isolation = bool(
        agent_os.user_isolation
        or (
            agent_os.authorization
            and agent_os.authorization_config is not None
            and agent_os.authorization_config.user_isolation
        )
    )
    db = agent_os._company_db
    from agno.company.routines import load_routine_skills

    return Agent(
        id=PRODUCT_MANAGER_ID,
        name="Product Manager",
        model=model,
        db=db,
        metadata={"_agno": {"internal": True, "id": PRODUCT_MANAGER_ID}},
        tools=[
            CompanyTools(
                db,
                user_isolation=isolation,
                decision_tools=False,
                summary_tools=False,
                refresh_tools=False,
                interfaces=agent_os.interfaces,
            )
        ],
        skills=load_routine_skills(),
        learning=LearningMachine(
            db=db, model=model, decision_log=CompanyDecisionLogStore(db, user_isolation=isolation)
        ),
        instructions=INSTRUCTIONS,
        add_datetime_to_context=True,
        add_history_to_context=True,
        num_history_runs=5,
    )
