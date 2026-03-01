import time
import json

from polling.loop import poll_once
from config import Settings


class DummyClient:
    def __init__(self, vehicles):
        self._vehicles = vehicles

    def get_vehicles(self):
        return self._vehicles


class DummyProducer:
    def __init__(self):
        self.messages = []

    def produce(self, topic, key, value, headers=None):
        self.messages.append((topic, key, value))

    def flush(self, timeout=10):
        pass


def test_poll_once_produces_per_vehicle(tmp_path):
    settings = Settings()
    settings.KAFKA_TOPIC = "test.topic"

    vehicles = {"response": [{"id": 1, "vin": "VIN1"}, {"id": 2, "vin": "VIN2"}]}
    client = DummyClient(vehicles)
    producer = DummyProducer()

    poll_once(settings, client, producer)

    assert len(producer.messages) == 2
    topics = {m[0] for m in producer.messages}
    assert "test.topic" in topics
