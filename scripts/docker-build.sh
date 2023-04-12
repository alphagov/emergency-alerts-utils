#! /bin/sh

PLATFORM=linux/amd64
# We can add linux/arm64 back in if we need it
REGION='eu-west-2'

while [ $# -gt 0 ]; do
  if [[ $1 == *"--"* ]]; then
    param="${1/--/}"
    declare $param="$2"
  fi
  shift
done

function get_account_number(){
  id=$(aws sts get-caller-identity)
  ECS_ACCOUNT_NUMBER=$(echo $id | jq -j .Account)
  if [[ -z $ECS_ACCOUNT_NUMBER ]]; then
    echo "Unable to find AWS account number"
    exit 1;
  fi
}

function ecr_login(){
  # aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com
}

function docker_build(){
  # if [ -z $EXECUTION_ID ] && [ -z $COMMIT_ID ]; then
  #   docker buildx build \
  #     --platform $PLATFORM \
  #     -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:latest \
  #     --build-arg ECS_ACCOUNT_NUMBER=$ECS_ACCOUNT_NUMBER \
  #     -f Dockerfile.eas-$IMAGE \
  #     --no-cache \
  #     $ARGS \
  #     .
  # else
  #   docker buildx build \
  #     --platform $PLATFORM \
  #     -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:pipeline-$EXECUTION_ID \
  #     -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:commit-$COMMIT_ID \
  #     -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:latest \
  #     --build-arg ECS_ACCOUNT_NUMBER=$ECS_ACCOUNT_NUMBER \
  #     -f Dockerfile.eas-$IMAGE \
  #     --no-cache \
  #     $ARGS \
  #     .
  # fi
  docker build --no-cache -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:latest -f Dockerfile.eas-$IMAGE .
}

get_account_number
ecr_login
docker_build
