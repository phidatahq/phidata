# LLM OS

This cookbook contains an initial implementation of the LLM OS proposed by [karpathy](https://twitter.com/karpathy/status/1723140519554105733).
He talks about it [in this tweet](https://twitter.com/karpathy/status/1723140519554105733), [this tweet](https://twitter.com/karpathy/status/1707437820045062561) and [this video](https://youtu.be/zjkBMFhNj_g?t=2535)

## The LLM OS philosophy

- LLMs are the kernel process of an emerging operating system.
- This process (LLM) will solve problems by coordinating other resources (like memory or computation tools).
- The LLM OS Vision:
  - [x] It can read/generate text
  - [x] It has more knowledge than any single human about all subjects
  - [x] It can browse the internet
  - [x] It can use existing software infra (calculator, python, mouse/keyboard)
  - [ ] It can see and generate images and video
  - [ ] It can hear and speak, and generate music
  - [ ] It can think for a long time using a system 2
  - [ ] It can “self-improve” in domains
  - [ ] It can be customized and fine-tuned for specific tasks
  - [x] It can communicate with other LLMs

[x] indicates functionality that is implemented in the LLM OS app

## Running the LLM OS:

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/llm_os/requirements.txt
```

### 3. Export credentials

- Out initial implementation uses GPT-4, so export your OpenAI API Key

```shell
export OPENAI_API_KEY=***
```

- To use Exa for research, export your EXA_API_KEY (get it from [here](https://dashboard.exa.ai/api-keys))

```shell
export EXA_API_KEY=xxx
```

### 4. Run PgVector

We use PgVector to provide long-term memory and knowledge to the LLM OS.
Please install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) and run PgVector using either the helper script or the `docker run` command.

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

### 5. Run the LLM OS App

```shell
streamlit run cookbook/llm_os/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your LLM OS.

### 6. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 7. Star ⭐️ the project if you like it.

### Share with your friends: https://git.new/llm-os
