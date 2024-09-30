import json
from pathlib import Path
from phi.assistant.duckdb import DuckDbAssistant

# ==== Let's test this sales AI and ask questions about sample sales data
# ==== Our goal is to test if this can do joins across multiple tables
sales_ai = DuckDbAssistant(
    name="sales_ai",
    use_tools=True,
    show_tool_calls=True,
    base_dir=Path(__file__).parent.joinpath("scratch"),
    instructions=["Get to the point, dont explain too much."],
    semantic_model=json.dumps(
        {
            "tables": [
                {
                    "name": "list_of_orders",
                    "description": "Contains information about orders",
                    "path": "https://ai-cookbook.s3.amazonaws.com/sales-analysis/list-of-orders.csv",
                },
                {
                    "name": "order_details",
                    "description": "Contains information about order details",
                    "path": "https://ai-cookbook.s3.amazonaws.com/sales-analysis/order-details.csv",
                },
                {
                    "name": "sales_targets",
                    "description": "Contains information about sales targets",
                    "path": "https://ai-cookbook.s3.amazonaws.com/sales-analysis/sales-targets.csv",
                },
            ]
        }
    ),
    # debug_mode=True,
)

sales_ai.cli_app(markdown=True)
