import os
from unittest.mock import patch

import pytest

from agno.exceptions import ModelAuthenticationError
from agno.models.linkrra import Linkrra
from agno.models.utils import get_model, get_model_from_dict


def test_linkrra_initialization_with_api_key():
    model = Linkrra(id="qwen3-coder-30b", api_key="test-api-key")
    assert model.id == "qwen3-coder-30b"
    assert model.api_key == "test-api-key"
    assert model.base_url == "https://pool.linkrra.com/v1"


def test_linkrra_initialization_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        model = Linkrra(id="qwen3-coder-30b")
        client_params = None
        with pytest.raises(ModelAuthenticationError):
            client_params = model._get_client_params()
        assert client_params is None


def test_linkrra_initialization_with_env_api_key():
    with patch.dict(os.environ, {"LINKRRA_API_KEY": "env-api-key"}):
        model = Linkrra(id="qwen3-coder-30b")
        assert model.api_key == "env-api-key"


def test_linkrra_client_params():
    model = Linkrra(id="qwen3-coder-30b", api_key="test-api-key")
    client_params = model._get_client_params()
    assert client_params["api_key"] == "test-api-key"
    assert client_params["base_url"] == "https://pool.linkrra.com/v1"


def test_linkrra_default_values():
    model = Linkrra(api_key="test-api-key")
    assert model.id == "qwen3-coder-30b"
    assert model.name == "Linkrra"
    assert model.provider == "Linkrra"


def test_linkrra_resolves_from_string_syntax():
    model = get_model("linkrra:qwen3-coder-30b")
    assert isinstance(model, Linkrra)
    assert model.id == "qwen3-coder-30b"


def test_linkrra_round_trips_through_dict():
    model = Linkrra(id="gpt-oss-20b", api_key="test-api-key")
    rebuilt = get_model_from_dict(model.to_dict())
    assert isinstance(rebuilt, Linkrra)
    assert rebuilt.id == "gpt-oss-20b"
