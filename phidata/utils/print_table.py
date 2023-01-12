from typing import Any, Dict, List, Optional

from rich.console import Console

console = Console()


def print_table(
    title: Optional[str] = None,
    header: Optional[List[str]] = None,
    rows: Optional[List[Dict[str, Any]]] = None,
) -> None:
    from rich import box
    from rich.table import Table

    table = Table(
        title=title,
        box=box.ASCII2,
        show_lines=True,
    )

    if header:
        for col in header:
            table.add_column(col, justify="center", no_wrap=True)

    if rows:
        for row in rows:
            row_values = [str(v) for v in row.values()]
            table.add_row(*row_values)

    if table.row_count > 0:
        console.print(table)
