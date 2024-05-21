# Deploying PDF Assistant with Docker Compose

Lets create a PDF Assistant that can answer questions from a PDF. We'll use `PgVector` for knowledge and storage.

**Knowledge Base:** information that the Assistant can search to improve its responses (uses a vector db).

**Storage:** provides long term memory for Assistants (uses a database).

### 1. Spin up resources

```shell
docker compose up --build
```

### 2. Spin down resources

```shell
docker compose down
```