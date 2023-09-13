<h1 align="center">
  phidata
</h1>
<p align="center">
    <em>AI Toolkit for Engineers</em>
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

[//]: # (<a href="https://github.com/phidatahq/phidata/actions/workflows/test.yml" target="_blank">)

[//]: # (    <img src="https://github.com/phidatahq/phidata/actions/workflows/test.yml/badge.svg" alt="test-status">)

[//]: # (</a>)

</p>

---

### Phidata is a toolkit for building LLM Apps, Web Apps and AI platforms.

- Phidata makes it easy to run tools like FastApi, Django, Jupyter, Streamlit, Airflow and Superset.
- Use these tools to build LLM Apps, Web Apps and Data Platforms.
- Run locally for development and production on AWS, with 1 command.

## 🚀 How it works

- **Create your codebase** from a template using `phi ws create`
- **Run your app locally** using `phi ws up dev:docker`
- **Run your app on AWS** using `phi ws up prd:aws`

## Basic Example: Run a Jupyter Notebook

### Requirements

- python 3.7+
- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/)

### Setup

Open the `terminal` and create a python virtual environment

```shell
python3 -m venv ~/.venvs/labenv
source ~/.venvs/labenv/bin/activate
```

Install `phidata`

```shell
pip install phidata
```

### Define `DockerConfig` that runs a `Jupyter` app

Create a file `resources.py` and add the following code to it

```python
from phidata.app.jupyter import Jupyter
from phidata.docker.config import DockerConfig

dev_docker_config = DockerConfig(
    apps=[
        # -*- Run Jupyter on port 8888
        Jupyter(mount_workspace=True)
    ],
)
```

### Start the app

```shell
phi start resources.py
```

- Open the browser and go to `http://localhost:8888`
- Password is `admin`

### Stop the app

```shell
phi stop resources.py
```

## More Information:

- **Documentation**: <a href="https://docs.phidata.com" target="_blank">https://docs.phidata.com</a>
- **Questions:** Chat with us on <a href="https://discord.gg/4MtYHHrgA8" target="_blank">Discord</a>
- **Email**: <a href="mailto:help@phidata.com" target="_blank">help@phidata.com</a>
