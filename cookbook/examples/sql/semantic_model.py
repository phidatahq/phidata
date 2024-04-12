import json


def get_nyc_semantic_model() -> str:
    return json.dumps(
        {
            "tables": [
                {
                    "table_name": "nyc_payroll_aggregated",
                    "table_description": "Contains aggregated payroll data for NYC agencies.",
                    "Use Case": "Use this table to get aggregated payroll data for NYC agencies or when the user asks for total payroll data from agencies.",
                },
                {
                    "table_name": "wegovnyc_citywide_payroll",
                    "table_description": "Contains raw payroll data for NYC agencies.",
                    "Use Case": "Use this table to get raw payroll data for NYC agencies or when the user asks a detailed payroll related question.",
                },
            ]
        },
        indent=4,
    )
