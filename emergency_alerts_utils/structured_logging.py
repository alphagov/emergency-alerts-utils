import json

from dataclasses import dataclass, asdict
from uuid import UUID


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
