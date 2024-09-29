from typing import Iterator

from phi.agent.response import AgentResponse
from phi.utils.timer import Timer


def pprint_agent_response_stream(
    response_stream: Iterator[AgentResponse], markdown: bool = False, show_time: bool = False
) -> None:
    from rich.live import Live
    from rich.table import Table
    from rich.status import Status
    from rich.box import ROUNDED
    from rich.markdown import Markdown

    _response_content: str = ""
    with Live() as live_log:
        status = Status("Working...", spinner="dots")
        live_log.update(status)
        response_timer = Timer()
        response_timer.start()
        for resp in response_stream:
            if isinstance(resp, AgentResponse) and isinstance(resp.content, str):
                _response_content += resp.content
            response_content = Markdown(_response_content) if markdown else _response_content

            table = Table(box=ROUNDED, border_style="blue", show_header=False)
            if show_time:
                table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", response_content)  # type: ignore
            else:
                table.add_row(response_content)  # type: ignore
            live_log.update(table)
        response_timer.stop()
