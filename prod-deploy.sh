#!/usr/bin/env bash
COMMIT_ID=$(git rev-parse --verify HEAD)
CLUSTER_NAME="YearnSimulationsInfraStack-YearnSimulationsCluster09747959-9VbPrg35xCGO"
SERVICE_NAME="YearnSimulationsInfraStack-SimulatorBotService0D0A55C9-5lKa7zoMP1xF"
TASK_NAME="YearnSimulationsInfraStackSimulatorBotTaskDefinition7FCDCB36"
CONTAINER_REPO="377926405243.dkr.ecr.us-east-1.amazonaws.com"

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${CONTAINER_REPO}
docker build --platform linux/x86_64 -t ${COMMIT_ID} .
docker tag ${COMMIT_ID} ${CONTAINER_REPO}/yearnsimulationsinfrastack-simulationsrepositorye85f502d-5bt86gznpt0m:${COMMIT_ID}
docker push ${CONTAINER_REPO}/yearnsimulationsinfrastack-simulationsrepositorye85f502d-5bt86gznpt0m:${COMMIT_ID}

./ecs-deploy -c ${CLUSTER_NAME} -n ${SERVICE_NAME} -i "${CONTAINER_REPO}/yearnsimulationsinfrastack-simulationsrepositorye85f502d-5bt86gznpt0m:${COMMIT_ID}"
