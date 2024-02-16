# Contributing to phidata

Phidata is an open-source project and we welcome contributions.

## 👩‍💻 How to contribute

Please follow the [fork and pull request](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) workflow:

- Fork the repository.
- Create a new branch for your feature.
- Add your feature or improvement.
- Send a pull request.
- We appreciate your support & input!

## Development setup

1. Clone the repository.
2. Create a virtual environment using the `./scripts/create_venv.sh` script. This will:
    - Create a `phienv` virtual environment in the current directory.
    - Install the required packages.
    - Install the `phidata` package in editable mode.
3. Activate the virtual environment using `source phienv/bin/activate`.

## Formatting and validation

We provide a `./scripts/format.sh` script that runs `ruff`, `mypy` and `pytest`.

Please run this script before submitting a pull request.

## Adding a new Vector Database

1. Setup your local environment by following the [Development setup](#development-setup).
2. Create a new directory under `phi/vectordb` for the new vector database.
3. Create a Class for your VectorDb that implements the `VectorDb` interface
   - Your Class will be in the `phi/vectordb/<your_db>/<your_db>.py` file.
   - The `VectorDb` interface is defined in `phi/vectordb/base
   - Import your `VectorDb` Class in `phi/vectordb/<your_db>/__init__.py`.
   - Checkout the [`phi/vectordb/pgvector/pgvector2`](https://github.com/phidatahq/phidata/blob/main/phi/vectordb/pgvector/pgvector2.py) file for an example.
4. Add a recipe for using your `VectorDb` under `cookbook/<your_db>`.
   - Checkout [`phidata/cookbook/pgvector`](https://github.com/phidatahq/phidata/tree/main/cookbook/pgvector) for an example (you do not need to add the `resources.py` file).
5. Important: Format and validate your code by running `./scripts/format.sh`.
6. Submit a pull request.

## Adding a new LLM provider

1. Setup your local environment by following the [Development setup](#development-setup).
2. Create a new directory under `phi/llm` for the new LLM provider.
3. If the LLM provider supports the OpenAI API spec:
   - Create a Class for your LLM provider that inherits the `OpenAILike` Class from `phi/llm/openai/like.py`.
   - Your Class will be in the `phi/llm/<your_llm>/<your_llm>.py` file.
   - Import your Class in the `phi/llm/<your_llm>/__init__.py` file.
   - Checkout the [`phi/llm/together/together.py`](https://github.com/phidatahq/phidata/blob/main/phi/llm/together/together.py) file for an example.
4. If the LLM provider does not support the OpenAI API spec:
   - Reach out to us on [Discord](https://discord.gg/4MtYHHrgA8) or open an issue to discuss the best way to integrate your LLM provider.
5. Add a recipe for using your LLM provider under `cookbook/<your_llm>`.
   - Checkout [`phidata/cookbook/together`](https://github.com/phidatahq/phidata/tree/main/cookbook/together) for an example.
6. Important: Format and validate your code by running `./scripts/format.sh`.
7. Submit a pull request.

Message us on [Discord](https://discord.gg/4MtYHHrgA8) if you have any questions or need help with credits.

## 📚 Resources

- <a href="https://docs.phidata.com/introduction" target="_blank" rel="noopener noreferrer">Documentation</a>
- <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">Discord</a>

## 📝 License

This project is licensed under the terms of the [MIT license](/LICENSE)

