# Clickhouse Agent

> Fork and clone the repository if needed.

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -U pypdf clickhouse-connect openai phidata
```

### 3. Run Clickhouse

> Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) first.

- Run using a helper script

```shell
./cookbook/run_clickhouse.sh
```

- OR run using the docker run command

```shell
docker run -d \
  -e CLICKHOUSE_DB=ai \
  -e CLICKHOUSE_USER=ai \
  -e CLICKHOUSE_PASSWORD=ai \
  -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 \
  -v clickhouse_data:/var/lib/clickhouse/ \
  -v clickhouse_log:/var/log/clickhouse-server/ \
  -p 8123:8123 \
  -p 9000:9000 \
  --ulimit nofile=262144:262144 \
  --name clickhouse-server \
  clickhouse/clickhouse-server
```

### 4. Run PgVector Agent

```shell
python cookbook/integrations/pgvector/agent.py
```
