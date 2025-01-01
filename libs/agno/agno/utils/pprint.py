import json
from typing import Union, Iterable

from pydantic import BaseModel

from phi.run.response import RunResponse
from phi.utils.timer import Timer
from phi.utils.log import logger


def pprint_run_response(
    run_response: Union[RunResponse, Iterable[RunResponse]], markdown: bool = False, show_time: bool = False
) -> None:
    from rich.live import Live
    from rich.table import Table
    from rich.status import Status
    from rich.box import ROUNDED
    from rich.markdown import Markdown
    from rich.json import JSON
    from phi.cli.console import console

    # If run_response is a single RunResponse, wrap it in a list to make it iterable
    if isinstance(run_response, RunResponse):
        single_response_content: Union[str, JSON, Markdown] = ""
        if isinstance(run_response.content, str):
            single_response_content = (
                Markdown(run_response.content) if markdown else run_response.get_content_as_string(indent=4)
            )
        elif isinstance(run_response.content, BaseModel):
            try:
                single_response_content = JSON(run_response.content.model_dump_json(exclude_none=True), indent=2)
            except Exception as e:
                logger.warning(f"Failed to convert response to Markdown: {e}")
        else:
            try:
                single_response_content = JSON(json.dumps(run_response.content), indent=4)
            except Exception as e:
                logger.warning(f"Failed to convert response to string: {e}")

        table = Table(box=ROUNDED, border_style="blue", show_header=False)
        table.add_row(single_response_content)
        console.print(table)
    else:
        streaming_response_content: str = ""
        with Live(console=console) as live_log:
            status = Status("Working...", spinner="dots")
            live_log.update(status)
            response_timer = Timer()
            response_timer.start()
            for resp in run_response:
                if isinstance(resp, RunResponse) and isinstance(resp.content, str):
                    streaming_response_content += resp.content

                formatted_response = Markdown(streaming_response_content) if markdown else streaming_response_content  # type: ignore
                table = Table(box=ROUNDED, border_style="blue", show_header=False)
                if show_time:
                    table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", formatted_response)  # type: ignore
                else:
                    table.add_row(formatted_response)  # type: ignore
                live_log.update(table)
            response_timer.stop()
