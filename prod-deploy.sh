#!/usr/bin/env bash
set -e 
set -o pipefail

COMMIT_ID=$(git rev-parse --verify HEAD)
CLUSTER_NAME="YearnSimulationsInfraStack-YearnSimulationsCluster09747959-GlcspAURHpm3"
SERVICE_NAME="YearnSimulationsInfraStack-SimulatorBotService0D0A55C9-mGtaPE99F9mZ"
CONTAINER_REPO="377926405243.dkr.ecr.us-east-1.amazonaws.com/sharedstack-simscheduledtasksrepository0bbaad80-2rca6gpnvzwc"

# Create a new container image and push it to the Container Repository
echo "Building new container image for commit: ${COMMIT_ID}"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${CONTAINER_REPO}
docker build --platform linux/x86_64 -t ${COMMIT_ID} .
docker tag ${COMMIT_ID} ${CONTAINER_REPO}:${COMMIT_ID}
docker tag ${COMMIT_ID} ${CONTAINER_REPO}:latest

docker push ${CONTAINER_REPO}:${COMMIT_ID}
docker push ${CONTAINER_REPO}:latest


echo "Deploying new task definition to... ${CLUSTER_NAME}"
./ecs-deploy -c ${CLUSTER_NAME} -n ${SERVICE_NAME} -i "${CONTAINER_REPO}:${COMMIT_ID}"