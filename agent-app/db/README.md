## Managing database migrations

This guide outlines the steps to manage database migrations for your workspace.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running Migrations](#running-migrations)
  - [Create a Database Revision](#create-a-database-revision)
  - [Migrate the Database](#migrate-the-database)
- [Environment-specific Instructions](#environment-specific-instructions)
  - [Development Environment](#development-environment)
  - [Production Environment](#production-environment)
- [Creating the Migrations Directory](#creating-the-migrations-directory)
- [Additional Resources](#additional-resources)

---

## Prerequisites

1. **Update Tables**: To run a migration, first we need to add or update SQLAlchemy tables in the `db/tables` directory.
2. **Import Classes**: Ensure that the SQLAlchemy table classes are imported in `db/tables/__init__.py`.

## Running Migrations

### Create a Database Revision

After you have added or updated your table, create a new database revision using:

```bash
alembic -c db/alembic.ini revision --autogenerate -m "Your Revision Message"
```

> **Note:** Replace `"Your Revision Message"` with a meaningful description of the changes.

### Migrate the Database by applying the revision

Run the migration to update the database schema:

```bash
alembic -c db/alembic.ini upgrade head
```

## Environment-specific Instructions

Let's explore the migration process for both development and production environments.

### Development Environment

**Create Revision and Migrate:**

```bash
docker exec -it agent-api alembic -c db/alembic.ini revision --autogenerate -m "Your Revision Message"
docker exec -it agent-api alembic -c db/alembic.ini upgrade head
```

### Production Environment

#### Option 1: Automatic Migration at Startup

Set the environment variable `MIGRATE_DB=True` to run migrations automatically when the container starts. This executes:

```bash
alembic -c db/alembic.ini upgrade head
```

#### Option 2: Manual Migration via SSH

SSH into the production container and run the migration manually:

```bash
ECS_CLUSTER=prd-agent-cluster
TASK_ARN=$(aws ecs list-tasks --cluster $ECS_CLUSTER --query "taskArns[0]" --output text)
CONTAINER_NAME=prd-agent-api

aws ecs execute-command --cluster $ECS_CLUSTER \
    --task $TASK_ARN \
    --container $CONTAINER_NAME \
    --interactive \
    --command "alembic -c db/alembic.ini upgrade head"
```

## Creating the Migrations Directory

> **Note:** These steps have already been completed and are included here for reference.

1. **Access the Development Container:**

    ```bash
    docker exec -it agent-api zsh
    ```

2. **Initialize Alembic Migrations:**

    ```bash
    cd db
    alembic init migrations
    ```

3. **Post-Initialization Steps:**

    - **Update `alembic.ini`:**
        - Set `script_location = db/migrations`.
    - **Update `migrations/env.py`:**
        - Modify according to the [Alembic Autogenerate Documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

## Additional Resources

- **Adding Database Tables:** Refer to the [Phidata documentation](https://docs.phidata.com/templates/how-to/database-tables) for detailed instructions on adding database tables.
- **Environment Variable Note:** Setting `MIGRATE_DB=True` ensures that the migration command runs from the entrypoint script when the container starts.
