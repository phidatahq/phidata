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

3. Edit the resources.py file and add your SingleStore database credentials.

4. Run SingleStore Assistant

```shell
python cookbook/singlestore/assistant.py
```

5. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions
