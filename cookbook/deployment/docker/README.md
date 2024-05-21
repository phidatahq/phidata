# Deploying PDF Assistant with Docker Compose

Lets deploy a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

### 1. Add OpenAI Key to Docker Compose .yml file
```
  assistant:
    build: .
    container_name: assistant
    depends_on:
      pgvector:
        condition: service_healthy
    environment:
      - DB_URL=postgresql+psycopg2://ai:ai@pgvector:5432/ai
      - OPENAI_API_KEY=sk-1234567890abcdef1234567890 # replace with your OpenAI API key
    volumes:
      - ./data/pdfs:/app/data/pdfs
```

### 2. Spin up resources

```shell
docker compose up --build
```

### 3. Spin down resources

```shell
docker compose down
```