<h1 align="center">
  phidata
</h1>
<p align="center">
    <em>Build data products as code</em>
</p>

<p align="center">
<a href="https://python.org/pypi/phidata" target="_blank">
    <img src="https://img.shields.io/pypi/v/phidata?color=blue&label=version" alt="version">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank">
    <img src="https://img.shields.io/badge/python->=3.7-blue" alt="pythonversion">
</a>
<a href="https://github.com/phidatahq/phidata" target="_blank">
    <img src="https://pepy.tech/badge/phidata" alt="downloads">
</a>
<a href="https://github.com/phidatahq/phidata/actions/workflows/build.yml" target="_blank">
    <img src="https://github.com/phidatahq/phidata/actions/workflows/build.yml/badge.svg" alt="build-status">
</a>
<a href="https://github.com/phidatahq/phidata/actions/workflows/test.yml" target="_blank">
    <img src="https://github.com/phidatahq/phidata/actions/workflows/test.yml/badge.svg" alt="test-status">
</a>
</p>

---

### Phidata is a toolkit for building high-quality, reliable data products.

Our goal is to create high quality tables, metrics and dashboards that can be used for analytics and machine learning.

Features:
1. Define your data products as code.
2. Build a data platform with dev and prd environments.
3. Manage tables as python objects and build a data lake as code.
4. Run Airflow and Superset locally on docker and production on aws.
5. Manage everything in 1 codebase using engineering best practices.

**Website**: <a href="https://phidata.com" target="_blank">phidata.com</a>

**Documentation**: <a href="https://docs.phidata.com" target="_blank">https://docs.phidata.com</a>

**Chat**: <a href="https://discord.gg/4MtYHHrgA8" target="_blank">discord</a>

---

## Quick start

Phidata is designed to build data products, so lets build example data products using cryptocurrency data.

To following along, you need:

- python 3.7+
- [docker desktop](https://docs.docker.com/desktop/install/mac-install/)

## Install phidata

Create a python virtual environment

```shell
python3 -m venv ~/.venvs/dpenv
source ~/.venvs/dpenv/bin/activate
```

Install and initialize phidata

```shell
pip install phidata
phi init
```

## Create workspace

**Workspace** is the directory containing the code for your data platform. It is version controlled using git and shared by your team. Data is a team sport and **code is the best way to collaborate**.

Run `phi ws init` to create a new workspace in the current directory. This will create a default scaffolding based on a blueprint. Press enter for defaults and create a workspace using the `aws` template.

```shell
phi ws init
```

cd into directory

```shell
cd data-platform
```

## Run Apps

**Apps** are open-source tools like airflow, superset and jupyter that run our data products.

Open **workspace/settings.py** and enable all apps on line 24.

```shell
pg_dbs_enabled: bool = True
superset_enabled: bool = True
jupyter_enabled: bool = True
airflow_enabled: bool = True
traefik_enabled: bool = True
whoami_enabled: bool = False
```

Then run `phi ws up` to create docker resources. Give 5 minutes for containers to start and the app to initialize.

```shell
phi ws up

Deploying workspace: data-platform

--**-- Docker env: dev
--**-- Confirm resources:
  -+-> Network: starter-aws
  -+-> Container: dev-pg-starter-aws-container
  -+-> Container: airflow-db-starter-aws-container
  -+-> Container: airflow-redis-starter-aws-container
  -+-> Container: airflow-ws-container
  -+-> Container: airflow-scheduler-container
  -+-> Container: airflow-worker-container
  -+-> Container: jupyter-container
  -+-> Container: superset-db-starter-aws-container
  -+-> Container: superset-redis-starter-aws-container
  -+-> Container: superset-ws-container
  -+-> Container: superset-init-container
  -+-> Container: traefik

Network: starter-aws
Total 13 resources
Confirm deploy [Y/n]:
```

### Checkout Superset

Open [localhost:8410](http://localhost:8410) in your browser to view the superset UI.

- User: admin
- Pass: admin
- Logs: `docker logs -f superset-ws-container`

### Checkout Airflow

Open [localhost:8310](http://localhost:8310) in a separate browser or private window to view the Airflow UI.

- User: admin
- Pass: admin
- Logs: `docker logs -f airflow-ws-container`

### Checkout Jupyter

Open [localhost:8888](http://localhost:888) in a browser to view the jupyterlab UI.

- Pass: admin
- Logs: `docker logs -f jupyter-container`

## Shutdown workspace

Shut down all resources using `phi ws down`:

```shell
phi ws down
```

or shut down using the app name:

```shell
phi ws down --app jupyter

phi ws down --app airflow

phi ws down --app superset
```
