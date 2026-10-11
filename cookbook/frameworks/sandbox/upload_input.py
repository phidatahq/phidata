"""Upload file bytes, then verify them from the completed checkpoint after a second turn."""

import os
from uuid import uuid4

import httpx


def main() -> None:
    headers = {}
    if os.environ.get("SANDBOX_BEARER_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["SANDBOX_BEARER_TOKEN"]
    session = "upload-" + uuid4().hex
    content = b"A file supplied by the API client.\n"
    with httpx.Client(
        base_url=os.environ.get("SANDBOX_API_URL", "http://localhost:7777"),
        headers=headers,
        timeout=120,
    ) as client:
        first = client.post(
            "/agents/coder/runs",
            data={
                "session_id": session,
                "message": "Read the attached file",
                "stream": "false",
            },
            files={"files": ("input.txt", content, "text/plain")},
        )
        first.raise_for_status()
        assert first.json()["status"] == "COMPLETED", first.text
        second = client.post(
            "/agents/coder/runs",
            data={
                "session_id": session,
                "message": "Continue without changing the attachment",
                "stream": "false",
            },
        )
        second.raise_for_status()
        assert second.json()["status"] == "COMPLETED", second.text
        endpoint = "/agents/coder/sessions/" + session + "/sandbox"
        listing = client.get(endpoint + "/artifacts")
        listing.raise_for_status()
        path = next(
            item["path"]
            for item in listing.json()["files"]
            if item["path"].endswith("/input.txt")
        )
        download = client.get(endpoint + "/artifact", params={"path": path})
        download.raise_for_status()
        assert download.content == content
        print("Attachment restored on the second turn:", session, path)


if __name__ == "__main__":
    main()
