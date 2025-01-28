# Universal Agent Interface (UAgI)

The Universal Agent Interface (UAgI) is a continuation of the LLM OS proposed by Andrej Karpathy [in this tweet](https://twitter.com/karpathy/status/1723140519554105733), [this tweet](https://twitter.com/karpathy/status/1707437820045062561) and [this video](https://youtu.be/zjkBMFhNj_g?t=2535).

It builds upon the LLM OS by adding:
- Multi-modal inputs and outputs
- Multi-agent coordination
- Reasoning

The core idea is that LLMs are the kernel process of an emerging operating system. This process (LLM) can solve problems by coordinating other resources (memory, computation tools).

### Current functionality:
  - [x] Can read/generate text, images, audio, video
  - [x] Has a dedicated knowledge base
  - [x] Can see and generate images and video
  - [x] Can search the web (using Exa) or scrape websites (using Firecrawl)
  - [x] Can use existing software infra (calculator, python)
  - [x] Can communicate with other Agents
  - [x] Can hear and speak

### Future functionality:
  - [ ] Can browse the internet (browser use)
  - [ ] Can “self-improve” or "learn" new domains
  - [ ] Can be customized and fine-tuned for specific tasks

<img alt="UAgI" src="https://github.com/phidatahq/phidata/assets/22579644/5cab9655-55a9-4027-80ac-badfeefa4c14" width="600" />


## Setup:

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/examples/apps/uagi/requirements.txt
```

### 3. Run PgVector

We'll use Postgres for storing data and knowledge. Run postgres in a docker container.

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
  agnohq/pgvector:16
```

### 4. Export credentials

We recommend using gpt-4o for this task, but you can use any Model you like.

```shell
export OPENAI_API_KEY=***
```

Other API keys are optional, but if you'd like to test:

```shell
export ANTHROPIC_API_KEY=***
export GOOGLE_API_KEY=***
export GROQ_API_KEY=***
```

- To use Exa for search, export your EXA_API_KEY (get it from [here](https://dashboard.exa.ai/api-keys))

```shell
export EXA_API_KEY=xxx
```

- To use Firecrawl for scraping, export your FIRECRAWL_API_KEY (get it from [here](https://firecrawl.ai/))

```shell
export FIRECRAWL_API_KEY=xxx
```

### 5. Run UAgI

```shell
streamlit run cookbook/examples/apps/uagi/app.py
```

- Open [localhost:8501](http://localhost:8501) to view the UAgI.
- Add a blog post to knowledge base: https://blog.samaltman.com/gpt-4o
- Ask: What is gpt-4o?
- Web search: What is happening in france?
- Calculator: What is 10!
- Enable shell tools and ask: Is docker running?
- Enable the Research Assistant and ask: Write a report on deepseek-reasoner
- Enable the Investment Assistant and ask: Shall I invest in nvda?
