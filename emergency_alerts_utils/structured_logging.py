import json
import os
import time
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from moto import mock_logs


@mock_logs
class LogData:
    b3client = None
    logGroupName = ""
    logStreamName = ""
    def __init__(self, source: str, module: str, method: str, serviceId: UUID = "", broadcastMessageId: UUID = ""):
        self.source = source
        self.module = module
        self.method = method
        self.serviceId = serviceId
        self.broadcastMessageId = broadcastMessageId

        LogData.logGroupName = os.environ.get("LOG_GROUP_NAME", "/aws/ecs/eas-app")
        LogData.logStreamName = os.environ.get("HOSTNAME", "placeholder")

        if LogData.b3client == None:
            try:
                LogData.b3client = boto3.client("logs", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
                LogData.b3client.create_log_stream(logGroupName=LogData.logGroupName, logStreamName=LogData.logStreamName)
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                    raise e

    def log_to_cloudwatch(self):
        if not LogData.b3client == None:
            try:
                LogData.b3client.put_log_events(
                    logGroupName=LogData.logGroupName,
                    logStreamName=LogData.logStreamName,
                    logEvents=[{"timestamp": int(round(time.time() * 1000)), "message": str(self)}],
                )
            except ClientError as e:
                raise e

    def __str__(self) -> str:
        return json.dumps(self.__dict__, cls=UUIDEncoder)

    def addData(self, attribute, value):
        setattr(self, attribute, value)


class UUIDEncoder(json.JSONEncoder):
    # Solution to the runtime error: [TypeError: Object of type UUID is not JSON serializable]
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
