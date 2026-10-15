"""Run the local Company API or mint a local test user's bearer token."""

import argparse
from os import environ

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS, Authorization, CompanyConfig, create_dev_token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--token-for", help="Print a one-hour local test token for this user and exit"
    )
    parser.add_argument("--db-file", default="tmp/company-os.db")
    parser.add_argument("--port", type=int, default=7777)
    args = parser.parse_args()
    secret = environ.get("COMPANY_DEMO_SECRET")
    if not secret:
        parser.error(
            "Set COMPANY_DEMO_SECRET to the same local signing key in both terminals"
        )
    if args.token_for:
        print(
            create_dev_token(
                args.token_for, secret=secret, scopes=["company:read", "company:write"]
            )
        )
        return

    agent_os = AgentOS(
        db=SqliteDb(db_file=args.db_file),
        company=CompanyConfig(),
        authorization=Authorization(verification_keys=[secret], algorithm="HS256"),
        auto_provision_dbs=False,
        telemetry=False,
    )
    agent_os.serve(agent_os.get_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
