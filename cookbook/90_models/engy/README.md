# Engy

Engy is an OpenAI-compatible API. Use Agno's `OpenAILike` model and point `base_url` at `https://api.engy.ai/v1`. No separate Engy package is required.

- Website: https://engy.ai/
- Docs: https://engy.ai/docs
- Contact: Terry Tse, terry@engy.ai

## Quick Start

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your `ENGY_API_KEY`

```shell
export ENGY_API_KEY=***
```

### 3. Install libraries

```shell
uv pip install -U openai agno
```

### 4. Run the example

```shell
python cookbook/90_models/engy/basic.py
```

## Example

```python
from os import getenv

from agno.agent import Agent
from agno.models.openai.like import OpenAILike

agent = Agent(
    model=OpenAILike(
        id="kimi-k3",
        api_key=getenv("ENGY_API_KEY"),
        base_url="https://api.engy.ai/v1",
    ),
    markdown=True,
)

agent.print_response("Share a 2 sentence horror story.")
```

`OpenAILike` sends the request to Engy's Chat Completions endpoint. Pass a model id from the models list. The example uses `kimi-k3`.

## Parameters

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `id` | `str` | `"not-provided"` | Model id. Engy flagships include `kimi-k3`, `glm-5.3`, `glm-5.3-flash`, and `deepseek-v4.1-flash-1017`. |
| `name` | `str` | `"OpenAILike"` | Name of the model instance |
| `provider` | `str` | `"OpenAI"` | Provider label inherited by `OpenAILike` |
| `api_key` | `Optional[str]` | `"not-provided"` | Engy API key. Read `ENGY_API_KEY` and pass it here. |
| `base_url` | `Optional[str]` | `None` | `https://api.engy.ai/v1` |

`OpenAILike` extends the OpenAI-compatible interface. Which parameters a given Engy model accepts is defined by Engy.

## Flagship models

Prices are USD per 1M tokens. The current catalog is `GET https://api.engy.ai/v1/models`.

| Model | Input | Output | Cache read |
| ----- | ----- | ------ | ---------- |
| `kimi-k3` | 1.95 | 9.75 | 0.195 |
| `glm-5.3` | 0.98 | 3.08 | 0.18 |
| `glm-5.3-flash` | 0.135 | 0.45 | 0.027 |
| `deepseek-v4.1-flash-1017` | 0.04 | 0.08 | 0.008 |

## API reference

- **Base URL**: `https://api.engy.ai/v1`
- **Models endpoint**: `https://api.engy.ai/v1/models`
- **API key environment variable**: `ENGY_API_KEY`
