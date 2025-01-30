# Game Generator Workflow

This is a simple game generator workflow that generates a single-page HTML5 game based on a user's prompt.

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install requirements

```shell
pip install -r cookbook/examples/apps/game_generator/requirements.txt
```

### 3. Export API Keys

We recommend using gemini for this task, but you can use any Model you like.

```shell
export GOOGLE_API_KEY=***
```

### 4. Run Streamlit App

```shell
streamlit run cookbook/examples/apps/game_generator/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the Game Generator.

### 7. Message us on [discord](https://agno.link/discord) if you have any questions
