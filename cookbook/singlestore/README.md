## Use SingleStore as Vector Storage for AI Apps

> Note: Fork and clone this repository if needed

1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

2. Install libraries

```shell
pip install -r cookbook/singlestore/requirements.txt
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

4. Run AI as a CLI Application

```shell
python cookbook/singlestore/cli.py
```

5. Run Streamlit application

```shell
streamlit run cookbook/singlestore/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your local AI app.
- Upload you own PDFs and ask questions

6. Message us on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions
