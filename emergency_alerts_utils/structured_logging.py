import boto3
import json
import os
import time

from botocore.exceptions import ClientError
from dataclasses import dataclass, asdict
from uuid import UUID


b3client = boto3.client("logs", region_name=os.environ.get('AWS_REGION'))
try:
    b3client.create_log_stream(
        logGroupName=os.environ.get('LOG_GROUP_NAME'),
        logStreamName=os.environ.get('HOSTNAME')
    )
except ClientError as e:
    if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
        raise e


@dataclass(frozen=True)
class LogData():
    source: str
    module: str
    method: str
    serviceId: UUID
    broadcastMessageId: UUID

    def __str__(self) -> str:
        return json.dumps(asdict(self), cls=UUIDEncoder)

class UUIDEncoder(json.JSONEncoder):
    # Solution to the runtime error: [TypeError: Object of type UUID is not JSON serializable]
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def log_to_cloudwatch(logData: LogData):
    try:
        b3client.put_log_events(
            logGroupName=os.environ.get('LOG_GROUP_NAME'),
            logStreamName=os.environ.get('HOSTNAME'),
            logEvents=[
                {
                    'timestamp': int(round(time.time() * 1000)),
                    'message': str(logData)
                }
            ]
        )
    except Exception as e:
        raise e
