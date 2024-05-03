# Journalist Team

Inspired by the fantastic work by [Matt Shumer (@mattshumer_)](https://twitter.com/mattshumer_/status/1772286375817011259).
We created an open-ended Journalist Team that uses 3 GPT-4 Assistants to write an article.
- Searcher: Finds the most relevant articles on the topic
- Writer: Writes a draft of the article
- Editor: Edits the draft to make it more coherent


### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install openai google-search-results newspaper3k lxml_html_clean phidata
```

### 3. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=sk-***
```

### 4. Run the Journalist Team to generate an article

```shell
python cookbook/teams/journalist/team.py
```
