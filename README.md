<h1 align="center">
  phidata
</h1>
<p align="center">
    <em>Building Blocks for Data Engineering</em>
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

### **Phidata is a set of building blocks for data engineering**

It makes data tools plug-n-play so teams can deliver high-quality, reliable data products

### How it works

- You start with a codebase that has data tools pre-configured
- Enable the Apps you need - Airflow, Superset, Jupyter, MLFlow
- Build data products (tables, metrics) in a dev environment running locally on docker
- Write pipelines in python or SQL. Use GPT-3 to generate boilerplate code
- Run production on AWS. Infrastructure is also pre-configured

### Advantages

- Automate the grunt work
- Recipes for common data tasks
- Everything is version controlled: Infra, Apps and Workflows
- Equal `dev` and `production` environments for data development at scale
- Multiple teams working together share code and define dependencies in a pythonic way
- Formatting (`black`), linting (`ruff`), type-checking (`mypy`) and testing (`pytest`) included

### More Information:

- **Website**: <a href="https://phidata.com" target="_blank">phidata.com</a>
- **Documentation**: <a href="https://docs.phidata.com" target="_blank">https://docs.phidata.com</a>
- **Chat**: <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>

---

## Quickstart

Let's build a data product using crypto data. Open the `Terminal` and follow along to download sample data and analyze it in a jupyter notebook.

## Setup

Create a python virtual environment

```bash
python3 -m venv ~/.venvs/dpenv
source ~/.venvs/dpenv/bin/activate
```

Install and initialize phidata

```bash
pip install phidata
phi init
```

> If you encounter errors, try updating pip using `python -m pip install --upgrade pip`

## Create workspace

**Workspace** is a directory containing the source code for your data platform. Run `phi ws init` to create a new workspace.

Press Enter to select the default name (`data-platform`) and template (`aws-data-platform`)

```bash
phi ws init
```

cd into the new workspace directory

```bash
cd data-platform
```

## Run your first workflow

The first step of building a data product is collecting the data. The `workflows/crypto/prices.py` file contains an example task for downloading crypto data locally to a CSV file. Run it using

```bash
phi wf run crypto/prices
```

Note how we define the output as a `CsvTableLocal` object with partitions and pre-write checks

```python
# Step 1: Define CsvTableLocal for storing data
# Path: `storage/tables/crypto_prices`
crypto_prices_local = CsvTableLocal(
    name="crypto_prices",
    database="crypto",
    partitions=["ds"],
    write_checks=[NotEmpty()],
)
```

Checkout `data-platform/storage/tables/crypto_prices` for the CSVs

## Run your first App

**Docker** is a great tool for testing locally. Your workspace comes pre-configured with a jupyter notebook for analyzing data. Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) and after the engine is running, start the workspace using

```bash
phi ws up
```

Press Enter to confirm. Verify the container is running using the docker dashboard or `docker ps`

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'

NAMES               IMAGE
jupyter-container   phidata/jupyter-aws-dp:dev
```

## Jupyter UI

Open [localhost:8888](http://localhost:8888) in a new tab to view the jupyterlab UI. Password: **admin**

Navigate to `notebooks/examples/crypto_prices.ipynb` and run all cells.

## Shutdown

Play around and then stop the workspace using


```bash
phi ws down
```


## Next

Checkout the [documentation](https://docs.phidata.com) for more information or chat with us on [discord](https://discord.gg/4MtYHHrgA8)

---
