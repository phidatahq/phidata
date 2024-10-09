## AI App

This repo contains the code for running an AI App in 2 environments:

1. `dev`: A development environment running locally on docker
2. `prd`: A production environment running on AWS ECS

## Setup Workspace

1. Clone the git repo

> from the `ai-app` dir:

2. Create + activate a virtual env:

```sh
python3 -m venv aienv
source aienv/bin/activate
```

3. Install `phidata`:

```sh
pip install phidata
```

4. Setup workspace:

```sh
phi ws setup
```

5. Copy `workspace/example_secrets` to `workspace/secrets`:

```sh
cp -r workspace/example_secrets workspace/secrets
```

6. Optional: Create `.env` file:

```sh
cp example.env .env
```

## Run AI App locally

1. Install [docker desktop](https://www.docker.com/products/docker-desktop)

2. Set OpenAI Key

Set the `OPENAI_API_KEY` environment variable using

```sh
export OPENAI_API_KEY=sk-***
```

**OR** set in the `.env` file

3. Start the workspace using:

```sh
phi ws up
```

- Open [localhost:8501](http://localhost:8501) to view the Streamlit App.
- If FastApi is enabled, Open [localhost:8000/docs](http://localhost:8000/docs) to view the FastApi docs.
- If Jupyter is enabled, open [localhost:8888](http://localhost:8888) to view JupyterLab UI.

4. Stop the workspace using:

```sh
phi ws down
```

## Next Steps:

- [Run the AI App on AWS](https://docs.phidata.com/templates/ai-app/run-aws)
- Read how to [manage the development application](https://docs.phidata.com/how-to/development-app)
- Read how to [manage the production application](https://docs.phidata.com/how-to/production-app)
- Read how to [add python libraries](https://docs.phidata.com/how-to/python-libraries)
- Read how to [format & validate your code](https://docs.phidata.com/how-to/format-and-validate)
- Read how to [manage secrets](https://docs.phidata.com/how-to/secrets)
- Add [CI/CD](https://docs.phidata.com/how-to/ci-cd)
- Add [database tables](https://docs.phidata.com/how-to/database-tables)
- Read the [AI App guide](https://docs.phidata.com/templates/ai-app)
