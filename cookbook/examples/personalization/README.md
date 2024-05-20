# ChatGPT like Memory for Agents

This cookbook implements Personalization i.e. ChatGPT like Memory for an Assistant.

Share details about yourself with the Assistant, and it will remember them across runs and personalize the responses to your preferences.
Similar to how [ChatGPT implements Memory](https://openai.com/index/memory-and-new-controls-for-chatgpt/).

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=***
```

### 3. Install libraries

```shell
pip install -r cookbook/examples/personalization/requirements.txt
```

### 4. Run PgVector

> Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) first.

- Run using a helper script

```shell
./cookbook/run_pgvector.sh
```

- OR run using the docker run command

```shell
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  phidata/pgvector:16
```

### 5. Run personalized Autonomous RAG App

```shell
streamlit run cookbook/examples/personalization/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the streamlit app.
- Enter a username to associate with the memory.
- Add to memory: "Call me bestie"
- Add to memory: "Always respond with a nice greeting and salutation"
- Add to memory: "I like docs so add a dog pun in the response"
- Add a website to the knowledge base: https://techcrunch.com/2024/04/18/meta-releases-llama-3-claims-its-among-the-best-open-models-available/
- Ask questions like:
  - What did Meta release?
  - Tell me more about the Llama 3 models?
  - Whats the latest news from Meta?
  - Summarize our conversation

### 6. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 7. Star ⭐️ the project if you like it.

### 8. Share with your friends: [https://git.new/auto-rag](https://git.new/auto-rag)
