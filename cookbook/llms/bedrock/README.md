# AWS Bedrock

> Note: Fork and clone this repository if needed

### 1. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export your AWS Credentials

```shell
export AWS_ACCESS_KEY_ID=***
export AWS_SECRET_ACCESS_KEY=***
```

### 3. Install libraries

```shell
pip install -U boto3 phidata
```

### 4. Run Assistant

- stream on

```shell
python cookbook/llms/bedrock/basic.py
```

- stream off

```shell
python cookbook/llms/bedrock/basic_stream_off.py
```
