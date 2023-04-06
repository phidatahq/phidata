## Data Platform

This repo contains the code for a data platform with 2 environments:

1. dev: A development platform running on docker
2. prd: A production platform running on aws + k8s

## Setup

1. Create + activate virtual env:

```sh
python3 -m venv .venv/dpenv
source .venv/dpenv/bin/activate
```

2. Install + init `phidata`:

```sh
pip install phidata
phi init -l
```

> If you encounter errors, try updating pip using `python -m pip install --upgrade pip`

3. Setup workspace:

```sh
phi ws setup
```

4. Copy secrets:

```sh
cp -r workspace/example_secrets workspace/secrets
```

5. Run dev platform on docker:

```sh
phi ws up dev:docker
```

If something fails, run again with debug logs:

```sh
phi ws up -d
```

Optional: Create `.env` file:

```sh
cp example.env .env
```

## Using the dev environment

The [workspace/dev](workspace/dev) directory contains the code for the dev environment. Run it using:

```sh
phi ws up dev:docker
```

### Run Airflow

1. Set `dev_airflow_enabled=True` in [workspace/settings.py](workspace/settings.py) and run `phi ws up dev:docker`
2. Check out the airflow webserver running in the `airflow-ws-container`:

- url: `http://localhost:8310/`
- user: `admin`
- pass: `admin`

### Run Jupyter

1. Set `dev_jupyter_enabled=True` in [workspace/settings.py](workspace/settings.py) and run `phi ws up dev:docker`
2. Check out jupyterlab running in the `jupyter-container`:

- url: `http://localhost:8888/`
- pass: `admin`

### Validate workspace

Validate the workspace using: `./scripts/validate.sh`

This will:

1. Format using black
2. Type check using mypy
3. Test using pytest
4. Lint using ruff

```sh
./scripts/validate.sh
```

If you need to install packages, run:

```sh
pip install black mypy pytest ruff
```

### Install workspace

Install the workspace & python packages in the virtual env using:

```sh
./scripts/install.sh
```

This will:

1. Install python packages from `requirements.txt`
2. Install the workspace in `--editable` mode

### Add python packages

Following [PEP-631](https://peps.python.org/pep-0631/), add dependencies to the [pyproject.toml](pyproject.toml) file.

To add a new package:

1. Add the module to the [pyproject.toml](pyproject.toml) file.
2. Run: `./scripts/upgrade.sh` to update the `requirements.txt` file.
3. Run `phi ws up dev:docker -f` to recreate images + containers

### Add airflow providers

Airflow requirements are stored in the [workspace/dev/airflow/resources/requirements-airflow.txt](/workspace/dev//airflow/resources/requirements-airflow.txt) file.

To add new airflow providers:

1. Add the module to the [workspace/dev/airflow/resources/requirements-airflow.txt](/workspace/dev/airflow/resources/requirements-airflow.txt) file.
2. Run `phi ws up -f --name airflow` to recreate images + containers

### Stop workspace

```sh
phi ws down
```

### Restart workspace

```sh
phi ws restart
```

### Add environment/secret variables

The containers read env using the `env_file` and secrets using the `secrets_file` params which by default point to files in the [workspace/env](workspace/env) and [workspace/secrets](workspace/secrets) directories.

#### Airflow

To add env variables to your airflow containers:

1. Update the [workspace/env/dev_airflow_env.yml](workspace/env/dev_airflow_env.yml) file.
2. Restart all airflow containers using: `phi ws restart dev:docker:airflow`

To add secret variables to your airflow containers:

1. Update the [workspace/secrets/dev_airflow_secrets.yml](workspace/secrets/dev_airflow_secrets.yml) file.
2. Restart all airflow containers using: `phi ws restart dev:docker:airflow`

### Test a DAG

```sh
# ssh into airflow-worker | airflow-ws
docker exec -it airflow-ws-container zsh
docker exec -it airflow-worker-container zsh

# Test run the DAGs using module name
python -m workflow.dir.file

# Test run the DAG file
python /mnt/workspaces/data-platform/workflow/dir/file.py

# List DAGs
airflow dags list

# List tasks in DAG
airflow tasks list \
  -S /mnt/workspaces/data-platform/workflow/dir/file.py \
  -t dag_name

# Test airflow task
airflow tasks test dag_name task_name 2022-07-01
```
