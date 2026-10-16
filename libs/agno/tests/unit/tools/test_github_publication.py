"""Publication logging stays scrubbed when the framework switches its default logger."""

import logging
from unittest.mock import MagicMock

import pytest
from github import GithubException

from agno.company.publish import _api
from agno.context.wiki.git_ops import Scrubber
from agno.tools.github import GithubTools


@pytest.mark.asyncio
async def test_publication_scrubs_the_toolkit_captured_logger(monkeypatch, caplog):
    token = "host-only-publication-secret"
    toolkit = GithubTools(access_token=token)
    repository = MagicMock()
    repository.create_pull.side_effect = GithubException(403, {"message": "refused " + token})
    monkeypatch.setattr(toolkit.g, "get_repo", lambda name: repository)
    # The GitHub toolkit already captured its own logger before this switch.
    monkeypatch.setattr("agno.utils.log.logger", logging.getLogger("company-test-other-logger"))
    with pytest.raises(ValueError, match="GitHub publication request failed") as error:
        await _api(
            toolkit, "create_pull_request", Scrubber([token]), "example/application", "Title", "Body", "head", "main"
        )
    assert token not in str(error.value) + caplog.text
    assert "***" in caplog.text
