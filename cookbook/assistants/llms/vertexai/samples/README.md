# Gemini Code Samples

This directory contains code samples for directly querying the Gemini API.
While these code samples don't use phidata, they are intended to help you test and get started with the Gemini API.

## Prerequisites

1. [Install](https://cloud.google.com/sdk/docs/install) the Google Cloud SDK
2. [Create a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
3. [Enable the AI Platform API](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com)
4. [Authenticate](https://cloud.google.com/sdk/docs/initializing) with Google Cloud

```shell
gcloud auth application-default login
```

5. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

6. Install `google-cloud-aiplatform` library

```shell
pip install -U google-cloud-aiplatform
```

7. Export the following environment variables

```shell
export PROJECT_ID=your-project-id
export LOCATION=us-central1
```

## Run the code samples

1. Multimodal example

```shell
python cookbook/llms/gemini/samples/multimodal.py
```
