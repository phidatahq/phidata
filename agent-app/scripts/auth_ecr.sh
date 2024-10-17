#!/bin/bash

set -e

# Authenticate with ecr
aws ecr get-login-password --region [AWS_REGION] | docker login --username AWS --password-stdin [AWS_ACCOUNT_ID].dkr.ecr.[AWS_REGION].amazonaws.com
