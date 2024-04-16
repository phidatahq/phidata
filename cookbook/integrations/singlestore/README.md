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

3. Run Assistant

```shell
python cookbook/integrations/singlestore/assistant.py
```
