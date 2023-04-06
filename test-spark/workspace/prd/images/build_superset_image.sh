#!/bin/bash

set -e

CURR_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOCKER_FILE="${CURR_SCRIPT_DIR}/superset.Dockerfile"
REPO="repo"
NAME="superset-aws-spark-dp"
TAG="prd"

# Run docker buildx create --use before running this script
echo "Running: docker buildx build --platform=linux/amd64,linux/arm64 -t $REPO/$NAME:$TAG  -f $DOCKER_FILE . --push"
docker buildx build --platform=linux/amd64,linux/arm64 -t $REPO/$NAME:$TAG  -f $DOCKER_FILE . --push
