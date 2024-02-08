## PDF Assistant with knowledge and storage

Lets create a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

1. Run PgVector

- Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) for running PgVector in a container.

```shell
phi start cookbook/pdf/resources.py -y
```

2. Install libraries

```shell
pip install -U pgvector pypdf psycopg sqlalchemy
```

3. Run PDF Assistant

```shell
python cookbook/pdf/assistant.py
```

- Ask a question:

```
How do I make pad thai?
```

- See how the Assistant searches the knowledge base and returns a response.

- Message `bye` to exit, start the assistant again using `python cookbook/pdf/assistant.py` and ask:

```
What was my last message?
```

- Run the `assistant.py` file with the `--new` flag to start a new run.

```shell
python pdf_assistant.py --new
```

4. Stop PgVector

```shell
phi stop cookbook/pdf/resources.py -y
```
