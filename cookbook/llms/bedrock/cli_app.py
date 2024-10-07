import typer

from phi.assistant import Assistant
from phi.llm.aws.claude import Claude

cli_app = typer.Typer(pretty_exceptions_show_locals=False)


@cli_app.command()
def aws_assistant():
    assistant = Assistant(
        llm=Claude(model="anthropic.claude-3-5-sonnet-20240620-v1:0"),
        instructions=["respond in a southern drawl"],
        debug_mode=True,
    )

    assistant.cli_app(markdown=True)


if __name__ == "__main__":
    cli_app()
