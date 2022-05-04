#!/bin/bash

############################################################################
#
# Entrypoint script for the Databox App
# This script:
#   - Sets sensible defaults.
#   - Waits for Postgres and Redis to be available if needed
#
############################################################################

############################################################################
# Set Defaults
############################################################################

if [[ "$PRINT_ENV_ON_LOAD" = true || "$PRINT_ENV_ON_LOAD" = True ]]; then
  echo "=================================================="
  # Databox env variables
  echo "PHI_DATA_DIR: $PHI_DATA_DIR"
  echo "PHI_PROJECTS_DIR: $PHI_PROJECTS_DIR"
  echo "INSTALL_REQUIREMENTS: $INSTALL_REQUIREMENTS"
  echo "REQUIREMENTS_FILE_PATH: $REQUIREMENTS_FILE_PATH"
  echo "PRINT_ENV_ON_LOAD: $PRINT_ENV_ON_LOAD"
  # Airflow env variables
  echo "WAIT_FOR_AIRFLOW_DB: $WAIT_FOR_AIRFLOW_DB"
  echo "WAIT_FOR_AIRFLOW_REDIS: $WAIT_FOR_AIRFLOW_REDIS"
  echo "AIRFLOW_DB_CONN_URL: $AIRFLOW_DB_CONN_URL"
  echo "AIRFLOW_DB_CONN_PORT: $AIRFLOW_DB_CONN_PORT"
  echo "AIRFLOW_DB_USER: $AIRFLOW_DB_USER"
  echo "AIRFLOW_DB_PASSWORD: $AIRFLOW_DB_PASSWORD"
  echo "AIRFLOW_SCHEMA: $AIRFLOW_SCHEMA"
  echo "AIRFLOW_REDIS_CONN_URL: $AIRFLOW_REDIS_CONN_URL"
  echo "AIRFLOW_REDIS_CONN_PORT: $AIRFLOW_REDIS_CONN_PORT"
  echo "AIRFLOW_REDIS_PASSWORD: $AIRFLOW_REDIS_PASSWORD"
  echo "AIRFLOW__CORE__DAGS_FOLDER: $AIRFLOW__CORE__DAGS_FOLDER"
  echo "=================================================="
fi

############################################################################
# Wait for Services
############################################################################

if [[ "$WAIT_FOR_AIRFLOW_DB" = true || "$WAIT_FOR_AIRFLOW_DB" = True ]]; then
  dockerize \
    -wait tcp://$AIRFLOW_DB_CONN_URL:$AIRFLOW_DB_CONN_PORT \
    -timeout 300s
fi

if [[ "$WAIT_FOR_AIRFLOW_REDIS" = true || "$WAIT_FOR_AIRFLOW_REDIS" = True ]]; then
  dockerize \
    -wait tcp://$AIRFLOW_REDIS_CONN_URL:$AIRFLOW_REDIS_CONN_PORT \
    -timeout 300s
fi

############################################################################
# Start the devbox
############################################################################

if [[ "$INSTALL_REQUIREMENTS" = true || "$INSTALL_REQUIREMENTS" = True ]]; then
  echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
  echo "Installing requirements from $REQUIREMENTS_FILE_PATH"
  pip3 install -U -r $REQUIREMENTS_FILE_PATH
  echo "Sleeping for 5 seconds..."
  sleep 5
  echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
fi


case "$1" in
  chill)
    ;;
  *)
    exec "$@"
    ;;
esac


echo ">>> Welcome to your Databox!"
while true; do sleep 18000; done
