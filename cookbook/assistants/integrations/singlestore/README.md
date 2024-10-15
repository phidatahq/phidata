## SingleStore Assistant

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U pymysql sqlalchemy pypdf openai phidata
```

3. Add credentials

- For SingleStore

> Note: If using a shared tier, please provide a certificate file for SSL connection [Read more](https://docs.singlestore.com/cloud/connect-to-your-workspace/connect-with-mysql/connect-with-mysql-client/connect-to-singlestore-helios-using-tls-ssl/)

```shell
export SINGLESTORE_HOST="host"
export SINGLESTORE_PORT="3333"
export SINGLESTORE_USERNAME="user"
export SINGLESTORE_PASSWORD="password"
export SINGLESTORE_DATABASE="db"
export SINGLESTORE_SSL_CA=".certs/singlestore_bundle.pem"
```

- Set your OPENAI_API_KEY

```shell
export OPENAI_API_KEY="sk-..."
```

4. Run Assistant

```shell
python cookbook/integrations/singlestore/assistant.py
```
