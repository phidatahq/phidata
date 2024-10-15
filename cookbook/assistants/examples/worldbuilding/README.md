# Exploring new worlds with OpenHermes and Ollama

> Note: Fork and clone this repository if needed

1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) and run ollama

```shell
ollama run openhermes
```

2. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

3. Install libraries

```shell
pip install -r cookbook/examples/worldbuilding/requirements.txt
```

4. Run World Builder Streamlit app

```shell
streamlit run cookbook/examples/worldbuilding/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your local AI app.
- Upload you own PDFs and ask questions

5. Optional: Run World Builder in the terminal

```shell
python cookbook/examples/worldbuilding/world_builder.py
```

6. Optional: Run World Explorer in the terminal

```shell
python cookbook/examples/worldbuilding/world_explorer.py
```

- Ask questions about your world

```text
Tell me about this world
```

7. Message me on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

8. Star ⭐️ the project if you like it.
