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
docker push ${CONTAINER_REPO}:${COMMIT_ID}


echo "Deploying new task definition to... ${CLUSTER_NAME}"
./ecs-deploy -c ${CLUSTER_NAME} -n ${SERVICE_NAME} -i "${CONTAINER_REPO}:${COMMIT_ID}"


scheduledEventRules=("YearnSimScheduledTasksInf-BribeBotTaskScheduledEve-RO3HPKJVVVEY" "YearnSimScheduledTasksInf-CreditsAvailableBotSched-L860DP254RWD" "YearnSimScheduledTasksInf-FTMBotScheduledEventRule-15BVCN7AUSDPD" "YearnSimScheduledTasksInf-SSCBotScheduledEventRule-18AQUOA1OFTWZ")
scheduledTasksDefinitions=("YearnSimScheduledTasksInfraStackBribeBotTaskScheduledTaskDefA3F2DC68" "YearnSimScheduledTasksInfraStackCreditsAvailableBotScheduledTaskDef37A3D671" "YearnSimScheduledTasksInfraStackFTMBotScheduledTaskDef9ED6D7D1" "YearnSimScheduledTasksInfraStackSSCBotScheduledTaskDef997EF41E")

for i in ${!scheduledEventRules[@]};
do
    echo "Updating task for Scheduled Event Rule ${scheduledEventRules[$i]} ..."

    echo "Creating new task definition..."
    # Get a template of the old task definition from the Scheduled Event Rule and use it as a template
    # to create a new task definition
    TASK_ARN=$(aws events list-targets-by-rule --rule ${scheduledEventRules[$i]} --query 'Targets[0].EcsParameters.TaskDefinitionArn' --output text)
    TASK_DEF=$(aws ecs describe-task-definition --task-definition ${TASK_ARN} | jq '.taskDefinition.containerDefinitions[0].image='\"${CONTAINER_REPO}:${COMMIT_ID}\" | jq '.taskDefinition' | jq -r '{containerDefinitions: .containerDefinitions, family: .family, taskRoleArn: .taskRoleArn, executionRoleArn: .executionRoleArn, networkMode: .networkMode, volumes: .volumes, requiresCompatibilities: .requiresCompatibilities, cpu: .cpu, memory: .memory}')

    echo "Registering new task definition..."
    # Register the new task definition
    REGISTERED_TASK=$(aws ecs register-task-definition --family "${scheduledTasksDefinitions[$i]}" --requires-compatibilities FARGATE --cli-input-json "${TASK_DEF}")
    NEW_TASK_ARN=$(echo $REGISTERED_TASK | jq -r '.taskDefinition.taskDefinitionArn')

    echo "Updating Scheduled Event Rule target..."
    # Update the Scheduled Event Rule Target to use the new task definition when the
    # event is triggered.
    EVENT_TARGET=$(aws events list-targets-by-rule --rule ${scheduledEventRules[$i]})
    NEW_EVENT_TARGET=$(echo $EVENT_TARGET | jq '.Targets[0].EcsParameters.TaskDefinitionArn='\"${NEW_TASK_ARN}\")
    aws events put-targets --no-cli-pager --rule ${scheduledEventRules[$i]} --cli-input-json "$NEW_EVENT_TARGET"
done