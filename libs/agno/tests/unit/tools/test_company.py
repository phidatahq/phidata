"""Optional Company arguments must work through raw and processed tools."""

import inspect
import json

import pytest

from agno.company import CompanyManager
from agno.db.sqlite import SqliteDb
from agno.run import RunContext
from agno.tools.company import CompanyTools


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("strict", [False, True])
def test_optional_schema_describes_null_and_hides_identity(tmp_path, use_async, strict):
    db = SqliteDb(db_file=str(tmp_path / "schema.db"))
    tools = CompanyTools(db)
    functions = tools.get_async_functions() if use_async else tools.functions
    for name, function in functions.items():
        signature = inspect.signature(getattr(tools, ("a" if use_async else "") + name))
        function.process_entrypoint(strict=strict)
        properties = function.parameters["properties"]
        assert "_agno_run_context" not in properties
        for argument, parameter in signature.parameters.items():
            if parameter.default is inspect.Parameter.empty or argument == "_agno_run_context":
                continue
            schema = properties[argument]
            assert schema["description"], (name, argument)
            assert len(schema["anyOf"]) == 2, (name, argument)
            assert {"type": "null"} in schema["anyOf"], (name, argument)
            assert all("enum" not in branch for branch in schema["anyOf"]), (name, argument)
    db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("processed", [False, True])
@pytest.mark.parametrize(
    "name", ["propose_company_task", "list_company_tasks", "list_company_wiki", "search_company_decisions"]
)
async def test_empty_optionals_equal_omission(tmp_path, use_async, processed, name):
    db = SqliteDb(db_file=str(tmp_path / "tools.db"))
    manager = CompanyManager(db)
    product = manager.create("SDK", user_id="alice")
    manager.create_task(product["id"], "Existing task")
    manager.log_decision("Review before shipping", agent_id="planner", session_id="prior")
    tools = CompanyTools(db)
    context = RunContext(run_id="run", session_id="session", user_id="alice")
    raw = getattr(tools, ("a" if use_async else "") + name)
    optional = [
        key
        for key, param in inspect.signature(raw).parameters.items()
        if param.default is not inspect.Parameter.empty and key != "_agno_run_context"
    ]
    if processed:
        function = (tools.get_async_functions() if use_async else tools.functions)[name]
        function.process_entrypoint()
        fn = function.entrypoint
    else:
        fn = raw
    required = {"product_id": product["id"], "title": "Proposed"} if name == "propose_company_task" else {}

    async def invoke(options):
        result = fn(**required, **options, _agno_run_context=context)
        result = json.loads(await result if inspect.isawaitable(result) else result)
        if name == "propose_company_task":
            for key in ("id", "session_id", "created_at", "updated_at"):
                result.pop(key, None)
        return result

    expected = await invoke({})
    if name != "propose_company_task":
        assert expected["meta"]["total_count"] > 0
    for argument in optional:
        assert await invoke({argument: ""}) == expected, argument
        assert await invoke({argument: None}) == expected, argument
    assert await invoke(dict.fromkeys(optional, "")) == expected
    db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("use_async", [False, True])
async def test_empty_optionals_do_not_weaken_required_validation(tmp_path, use_async):
    tools = CompanyTools(SqliteDb(db_file=str(tmp_path / "validation.db")))
    manager = CompanyManager(tools.db)
    product = manager.create("SDK")
    fn = tools.apropose_company_task if use_async else tools.propose_company_task
    with pytest.raises(ValueError, match="title"):
        result = fn(product["id"], "", project_id="")
        if inspect.isawaitable(result):
            await result
    with pytest.raises(ValueError):
        result = fn(product["id"], "Valid title", project_id=" ")
        if inspect.isawaitable(result):
            await result
    tools.db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("processed", [False, True])
@pytest.mark.parametrize("name", ["list_company_sources", "read_company_source"])
async def test_source_optionals_equal_omission(tmp_path, use_async, processed, name):
    db = SqliteDb(db_file=str(tmp_path / "sources.db"))
    manager = CompanyManager(db)
    product = manager.create("SDK")
    path = tmp_path / "source.md"
    path.write_text("Observed content")
    source = manager.create_source(product["id"], "markdown", str(path))
    tools = CompanyTools(db)
    context = RunContext(run_id="scan", session_id="session", user_id="alice")
    raw = getattr(tools, ("a" if use_async else "") + name)
    optional = [
        key
        for key, param in inspect.signature(raw).parameters.items()
        if param.default is not inspect.Parameter.empty and key != "_agno_run_context"
    ]
    fn = raw
    if processed:
        function = (tools.get_async_functions() if use_async else tools.functions)[name]
        function.process_entrypoint()
        fn = function.entrypoint
    required = {"product_id": product["id"]} if name == "list_company_sources" else {"source_id": source["id"]}

    async def invoke(options):
        result = fn(**required, **options, _agno_run_context=context)
        return json.loads(await result if inspect.isawaitable(result) else result)

    expected = await invoke({})
    for argument in optional:
        assert await invoke({argument: ""}) == expected, argument
        assert await invoke({argument: None}) == expected, argument
    if name == "read_company_source":
        selected = await invoke({"path": path.name, "max_chars": None, "content_offset": ""})
        assert selected["content"] == "Observed content"
    db.close()
