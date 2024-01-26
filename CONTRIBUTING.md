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

1. Get your local environment setup by following the [Development setup](#development-setup).
2. Create a new directory in `phi/vectordb` with the name of the vector database.
3. Implement the `VectorDb` interface in `phi/vectordb/<your_db>/<your_db>.py`.
4. Import your `VectorDb` implementation in `phi/vectordb/<your_db>/__init__.py`.
5. Add a recipe for using your `VectorDb` in `cookbook/<your_db>/assistant.py`.
6. Format and validate your code by running `./scripts/format.sh`.
6. Submit a pull request.

## 📚 Resources

- <a href="https://docs.phidata.com/introduction" target="_blank" rel="noopener noreferrer">Documentation</a>
- <a href="https://discord.gg/4MtYHHrgA8" target="_blank" rel="noopener noreferrer">Discord</a>

## 📝 License

This project is licensed under the terms of the [MIT license](/LICENSE)

