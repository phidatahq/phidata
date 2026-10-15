"""Send an image and a file to a sandboxed Claude agent.

Build the runtime image, run Postgres, and export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN:

    .venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
    ./cookbook/scripts/run_pgvector.sh
    .venv/bin/python cookbook/frameworks/sandbox/sandbox_attachments.py

The attachments are written into the sandbox workspace under .agno/uploads/<run_id>/ and named
in the prompt, so Claude Code opens them with its own tools. They are part of the turn's
checkpoint, so a later turn on a new computer can still read them. A request carries at most
16 attachments and 512 KiB in total; audio and video are rejected.
"""

import base64
import os
from uuid import uuid4

from agno.agents.claude import ClaudeAgent
from agno.db.postgres import PostgresDb
from agno.media import File, Image
from agno.sandbox.docker import DockerSandbox

# A 1x1 red PNG, so the example needs no image on disk.
RED_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)

agent = ClaudeAgent(
    id="reader",
    model="claude-sonnet-4-6",
    permission_mode="bypassPermissions",
    db=PostgresDb(
        db_url=os.getenv(
            "AGNO_SANDBOX_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
        )
    ),
    sandbox=DockerSandbox(
        os.getenv("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
        network="isolated",
        memory_mb=1024,
    ),
)

session_id = "sandbox-attachments-" + uuid4().hex[:8]

first = agent.run(
    "What colour is the attached image, and what is the release date in the attached notes? "
    "Answer in one line.",
    session_id=session_id,
    images=[Image(content=RED_PIXEL, format="png")],
    files=[
        File(
            content=b"Release date: 2026-11-02\nOwner: platform team\n",
            filename="release-notes.txt",
        )
    ],
)
print("Turn 1:", first.status.value, "-", first.content)

# No attachments this time: the file from turn 1 is restored with the checkpoint.
second = agent.run(
    "Who owns the release, according to the notes I sent earlier? Answer with the owner only.",
    session_id=session_id,
)
print("Turn 2:", second.status.value, "-", second.content)
