"""A model-free Company deployment. Apply migrations before starting this app."""

from os import environ

from agno.db.postgres import PostgresDb
from agno.os import AgentOS, Authorization, CompanyConfig, UserDirectory

# Set JWT_VERIFY_KEY to your identity provider's public verification key.
# HS256 is supported for local testing; production deployments should use their
# identity provider's verification algorithm, audience, and issuer.
company_db = PostgresDb(db_url=environ["COMPANY_DATABASE_URL"])
users = UserDirectory(db=company_db, auto_provision=False)
authorization = Authorization(
    verification_keys=[environ["JWT_VERIFY_KEY"]],
    algorithm=environ.get("JWT_ALGORITHM", "RS256"),
    audience=environ.get("AGENT_OS_ID", "company-manual"),
)
agent_os = AgentOS(
    id=environ.get("AGENT_OS_ID", "company-manual"),
    company=CompanyConfig(db=company_db),
    authorization=authorization,
    user_directory=users,
)
app = agent_os.get_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7777)
