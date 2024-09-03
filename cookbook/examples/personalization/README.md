# Personalized Agentic RAG

This cookbook implements Personalized Agentic RAG.
Meaning it will remember details about the user and personalize the responses, similar to how [ChatGPT implements Memory](https://openai.com/index/memory-and-new-controls-for-chatgpt/).

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Export credentials

- We use gpt-4o as the LLM, so export your OpenAI API Key

```shell
export OPENAI_API_KEY=***
```

- To use Exa for research, export your EXA_API_KEY (get it from [here](https://dashboard.exa.ai/api-keys))

```shell
export EXA_API_KEY=xxx
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

### 5. Run streamlit app

```shell
streamlit run cookbook/examples/personalization/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the streamlit app.
- Enter a username to associate with the memory.
- Add to memory: "I live in New York so always include a New York reference in the response"
- Add to memory: "I like dogs so always include a dog pun in the response"
- Ask questions like:
  - Compare nvidia and amd, use all the tools available
  - Whats happening in france?
  - Summarize our conversation
- Add a blog post to the knowledge base: https://blog.samaltman.com/what-i-wish-someone-had-told-me
- Ask questions like:
  - What does Sam Altman wish someone had told him?

### 6. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 7. Star ⭐️ the project if you like it.

### 8. Share with your friends: [https://git.new/personalization](https://git.new/personalization)
