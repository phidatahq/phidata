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

Use phidata to create tables, metrics and dashboards for analytics and machine learning.

Features:
- Build data products as code.
- Build a data platform with dev and production environments.
- Manage tables as python objects and build a data lake as code.
- Run Airflow and Superset locally on docker and production on aws.
- Manage everything in 1 codebase using engineering best practices.

More Information:
- **Website**: <a href="https://phidata.com" target="_blank">phidata.com</a>
- **Documentation**: <a href="https://docs.phidata.com" target="_blank">https://docs.phidata.com</a>
- **Chat**: <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>

---

## Quick start

This guide shows how to:
1. Run Airflow, Superset, Jupyter and Postgres locally on docker.
2. Run workflows and create postgres tables.

To follow along, you need:

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

**Workspace** is the directory containing the code for your data platform. It is version controlled using git and shared with your team.

Run `phi ws init` to create a new workspace in the current directory. Press enter to create a default workspace using the `aws` blueprint.

```shell
phi ws init
```

cd into directory

```shell
cd data-platform
```

## Run Apps

**Apps** are open-source tools like airflow, superset and jupyter that run the data products.

Open **workspace/settings.py** and enable the apps you want to run (line 24). Note: Each app uses a lot of memory so you may need to increase the memory allocated to docker.

```shell
pg_dbs_enabled: bool = True
superset_enabled: bool = True
jupyter_enabled: bool = True
airflow_enabled: bool = True
traefik_enabled: bool = True
```

Then run `phi ws up` to create docker resources. Give 5 minutes for containers to start and the apps to initialize.

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

## Run workflows

### Install dependencies

Before running workflows, we need to install dependencies like `pandas` and `sqlalchemy`.
The workspace includes a script to install dependencies, run it:

```shell
./scripts/install.sh
```

**Or** install dependencies manually using pip:

```shell
pip install --editable ".[dev]"
```

### Download crypto prices to a file

The **workflows/crypto/prices.py** file contains a task that pulls crypto prices from coingecko.com and stores them at `storage/crypto/crypto_prices.csv`. Run it using the `phi wf run` command:

```shell
phi wf run crypto/prices
```

Note how we define the file as a **File** object:

```shell
crypto_prices_file = File(
    name="crypto_prices.csv",
    file_dir="crypto",
)
```

While this works as a toy example, storing data locally is not of much use. We want to either load this data to a database or store it in cloud storage like s3.

Let's load this data to a postgres table running locally on docker.

### Download crypto prices to a postgres table

The **workflows/crypto/prices_pg.py** file contains a workflow that loads crypto price data to a postgres table: `crypto_prices_daily`. Run it using the `phi wf run` command:

```shell
phi wf run crypto/prices_pg
```

We define the table using a **PostgresTable** object:

```shell
crypto_prices_daily_pg = PostgresTable(
    name="crypto_prices_daily",
    db_app=PG_DB_APP,
    airflow_conn_id=PG_DB_CONN_ID,
)
```

You can now query the table using the database tool of your choice.

Credentials:
- Host: 127.0.0.1
- Port: 5432
- User: starter-aws
- Pass: starter-aws
- Database: starter-aws

> We're big fans of [TablePlus](https://tableplus.com/) for database management.

## Next steps

1. [Deploy to AWS](https://docs.phidata.com/aws/setup).
2. [Enable traefik](https://docs.phidata.com/local/traefik-docker) and use `airflow.dp` and `superset.dp` local domains.
3. Read the [documentation](https://docs.phidata.com) to learn more about phidata.


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

## More Information:
- **Website**: <a href="https://phidata.com" target="_blank">phidata.com</a>
- **Documentation**: <a href="https://docs.phidata.com" target="_blank">https://docs.phidata.com</a>
- **Chat**: <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>

---
