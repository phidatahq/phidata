# Gemini Cookbook

> Note: Fork and clone this repository if needed

## Prerequisites

1. [Install](https://cloud.google.com/sdk/docs/install) the Google Cloud SDK
2. [Create a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
3. [Enable the AI Platform API](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com)
4. [Authenticate](https://cloud.google.com/sdk/docs/initializing) with Google Cloud

```shell
gcloud auth application-default login
```

## Build Assistants using Gemini

1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U google-cloud-aiplatform phidata
```

3. Export the following environment variables

```shell
export PROJECT_ID=your-project-id
export LOCATION=us-central1
```

4. Run Assistant

```shell
python cookbook/llms/gemini/assistant.py
```

5. Run Assistant with Tool calls

```shell
pip install duckduckgo-search

python cookbook/llms/gemini/tool_call.py
```
