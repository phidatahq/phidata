## SingleStore Assistant

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U pypdf pymysql sqlalchemy openai phidata
```

3. Provide SingleStore database credentials

You can provide the SingleStore database credentials in the following ways:

- Add the SingleStore database credentials to the resources.py file

or

- Export the SingleStore database credentials as environment variables

```shell
export SINGLESTORE_HOST="host"
export SINGLESTORE_PORT="3333"
export SINGLESTORE_USERNAME="user"
export SINGLESTORE_PASSWORD="password"
export SINGLESTORE_DATABASE="db"
export SINGLESTORE_SSL_CERT=".certs/singlestore_bundle.pem"
```

4. Run SingleStore Assistant

```shell
python cookbook/singlestore/assistant.py
```

5. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions
