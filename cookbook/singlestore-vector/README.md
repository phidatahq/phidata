## singlestore Assistant

1. Run singlestore

```shell
phi start cookbook/singlestore-vector/resources.py -y
```

2. Install libraries

```shell
pip install -U pypdf pymysql sqlalchemy
```

3. Run singlestore Assistant

```shell
python cookbook/singlestore-vector/assistant.py
```

4. Turn off singlestore

```shell
phi stop cookbook/singlestore-vector/resources.py -y
```
