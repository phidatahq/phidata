"""Product reports use the configured interface's existing outbound transport."""

import asyncio
import os
from typing import Any, Dict, Sequence


def _summary_report(product: Any, counts: Any, tasks: Any, narrative: str, previous: str) -> str:
    """Compare stored Task facts with the preceding report and retain the executor's narrative."""
    import base64
    import json
    import re

    if not isinstance(narrative, str) or not narrative.strip():
        raise ValueError("Summary requires the executor's narrative")
    prior: Dict[str, Any] = {}
    snapshots = re.findall(r"<!-- Company delivered snapshot: ([A-Za-z0-9+/=]+) -->", previous)
    if snapshots:
        try:
            prior = json.loads(base64.b64decode(snapshots[-1]))
            if not isinstance(prior, dict):
                prior = {}
        except (ValueError, UnicodeDecodeError):
            prior = {}
    current: Dict[str, Any] = {}
    failures = []
    waiting = []
    for task in tasks:
        result = task.get("result") or {}
        status = str(result.get("status") or "").upper()
        error = (
            str(result.get("error") or result.get("content") or "No failure detail recorded")
            if status in {"ERROR", "FAILED", "CANCELLED"}
            else None
        )
        current[task["id"]] = {"title": task["title"], "status": task["status"], "run_status": status, "error": error}
        if error:
            failures.append("- " + task["title"] + " (" + task["id"] + "): " + status + ": " + error)
        if task["status"] in {"backlog", "in_review"}:
            waiting.append("- " + task["title"] + ": " + task["status"])
    changes = []
    for task_id, state in current.items():
        old = prior.get(task_id)
        if old is None:
            changes.append("- Added " + state["title"] + ": " + state["status"])
        elif old != state:
            changes.append(
                "- "
                + state["title"]
                + ": "
                + str(old.get("status"))
                + " → "
                + state["status"]
                + ("; run " + state["run_status"] if state["run_status"] else "")
            )
    for task_id in prior.keys() - current.keys():
        changes.append("- No longer visible: " + str(prior[task_id].get("title", task_id)))
    snapshot = base64.b64encode(json.dumps(current, sort_keys=True).encode()).decode()
    return (
        "# "
        + product["name"]
        + " summary\n\n"
        + "\n".join(f"{name}: {count}" for name, count in counts.items())
        + "\n\n## Narrative\n\n"
        + narrative.strip()
        + "\n\n## What changed\n\n"
        + ("\n".join(changes) or "No Task changes since the last delivered summary.")
        + "\n\n## Waiting on the owner\n\n"
        + ("\n".join(waiting) or "Nothing awaiting the owner.")
        + "\n\n## Failed Tasks\n\n"
        + ("\n".join(failures) or "No failed Tasks.")
        + ("\n\nQuiet successful check: no work requires attention." if not tasks else "")
        + "\n\n<!-- Company summary snapshot: "
        + snapshot
        + " -->\n"
    )


def _summary_page(previous: str, run_id: str, report: str):
    """Keep delivery receipts on one versioned page, including intervening runs."""
    import re

    from agno.utils.string import hash_string_sha256

    if not run_id:
        raise ValueError("Summary requires a run id")
    marker = "\n<!-- Delivered run: " + hash_string_sha256(run_id) + " -->\n"
    receipts = re.findall(r"\n<!-- Delivered run: [a-f0-9]{64} -->\n", previous)
    baseline = re.findall(r"<!-- Company delivered snapshot: ([A-Za-z0-9+/=]+) -->", previous)
    # Legacy or never-delivered pages have no trusted delivery baseline: report all current Tasks once.
    snapshot = baseline[-1] if baseline else "e30="
    pending = report + "\n<!-- Company delivered snapshot: " + snapshot + " -->\n" + "".join(receipts)
    return pending, marker in receipts, marker


def _summary_delivered(report: str, marker: str) -> str:
    """Advance the baseline only with the delivery receipt, after transport succeeds."""
    import re

    current = re.findall(r"<!-- Company summary snapshot: ([A-Za-z0-9+/=]+) -->", report)
    baseline = list(re.finditer(r"<!-- Company delivered snapshot: [A-Za-z0-9+/=]+ -->", report))
    if not current or not baseline:
        raise ValueError("Summary snapshot is missing")
    last = baseline[-1]
    return (
        report[: last.start()]
        + "<!-- Company delivered snapshot: "
        + current[-1]
        + " -->"
        + report[last.end() :]
        + marker
    )


async def adeliver_summary(interfaces: Sequence[Any], interface_type: str, destination: str, message: str) -> None:
    """Deliver to a human-configured destination; credentials remain inside the interface."""
    interface = next((item for item in interfaces if item.type == interface_type), None)
    if interface is None:
        raise ValueError("Summary interface is not configured on AgentOS")
    if interface_type == "slack":
        from slack_sdk.web.async_client import AsyncWebClient

        from agno.os.interfaces.slack.helpers import send_slack_message_async

        client = AsyncWebClient(token=interface.token or os.getenv("SLACK_TOKEN"), ssl=interface.ssl)
        await send_slack_message_async(client, destination, "", message)
    elif interface_type == "telegram":
        from telebot.async_telebot import AsyncTeleBot

        from agno.os.interfaces.telegram.helpers import send_message

        token = interface.token or os.getenv("TELEGRAM_TOKEN")
        if not isinstance(token, str) or not token:
            raise ValueError("Telegram interface token is not configured")
        bot = AsyncTeleBot(token)
        try:
            await send_message(bot, int(destination), message)
        finally:
            await bot.close_session()
    elif interface_type == "whatsapp":
        from agno.os.interfaces.whatsapp.helpers import WhatsAppConfig, send_whatsapp_message_async

        config = WhatsAppConfig.init(access_token=interface.access_token, phone_number_id=interface.phone_number_id)
        await send_whatsapp_message_async(destination, message, config)
    else:
        raise ValueError("Summary requires a Slack, Telegram or WhatsApp interface")


def deliver_summary(interfaces: Sequence[Any], interface_type: str, destination: str, message: str) -> None:
    """Synchronous counterpart for code-managed reports."""
    asyncio.run(adeliver_summary(interfaces, interface_type, destination, message))
