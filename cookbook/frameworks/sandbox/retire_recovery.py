"""Exercise retirement and recovery deletion on a fresh fixture session only."""

import os
from uuid import uuid4

import httpx

session_id = "lifecycle-example-" + uuid4().hex
headers = {}
if os.environ.get("SANDBOX_BEARER_TOKEN"):
    headers["Authorization"] = "Bearer " + os.environ["SANDBOX_BEARER_TOKEN"]
with httpx.Client(
    base_url=os.environ.get("SANDBOX_API_URL", "http://localhost:7777"),
    headers=headers,
    timeout=60,
) as client:
    print("Fresh fixture session:", session_id)
    first = client.post(
        "/agents/coder/runs",
        data={
            "message": "lifecycle fixture",
            "session_id": session_id,
            "stream": "false",
        },
    )
    first.raise_for_status()
    assert first.json()["status"] == "COMPLETED"
    endpoint = "/agents/coder/sessions/" + session_id + "/sandbox"
    protected = client.delete("/sessions/" + session_id)
    assert protected.status_code == 409, protected.text
    retired = client.post(endpoint + "/retire")
    retired.raise_for_status()
    artifact = client.get(
        endpoint + "/artifact", params={"path": "fixture-effects.txt"}
    )
    artifact.raise_for_status()
    assert artifact.text == first.json()["run_id"] + "\n"
    purged = client.delete(endpoint + "/recovery")
    purged.raise_for_status()
    assert purged.json()["conversation_retained"]
    assert client.get(endpoint + "/artifacts").status_code == 404
    deleted = client.delete("/sessions/" + session_id)
    assert deleted.status_code == 204, deleted.text
    print(
        "Retirement preserved the artifact. Recovery purge then allowed conversation deletion."
    )
