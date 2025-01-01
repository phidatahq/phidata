## SingleStore Agent

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -U pymysql sqlalchemy pypdf openai phidata
```

3. Run SingleStore

```shell
docker run \                                          
    -d --name singlestoredb-dev \
    -e ROOT_PASSWORD="admin" \                              
    -p 3306:3306 -p 8080:8080 -p 9000:9000 \
    --platform linux/amd64 \
    ghcr.io/singlestore-labs/singlestoredb-dev:latest
```

4. Create the database

- Visit http://localhost:8080 and login with `root` and `admin`
- Create the database with your choice of name

5. Add credentials

- For SingleStore

```shell
export SINGLESTORE_HOST="localhost"
export SINGLESTORE_PORT="3306"
export SINGLESTORE_USERNAME="root"
export SINGLESTORE_PASSWORD="admin"
export SINGLESTORE_DATABASE="your_database_name" 
export SINGLESTORE_SSL_CA=".certs/singlestore_bundle.pem"
```

- Set your OPENAI_API_KEY

```shell
export OPENAI_API_KEY="sk-..."
```

4. Run Agent

```shell
python cookbook/integrations/singlestore/agent.py
```
