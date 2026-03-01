from typing import Dict, Optional

try:
    from confluent_kafka import Producer
    _HAVE_CONFLUENT = True
except Exception:
    Producer = None  # type: ignore
    _HAVE_CONFLUENT = False


class KafkaProducerWrapper:
    """Kafka producer wrapper - uses confluent_kafka if available, otherwise a noop logger.

    This keeps the code testable without a Kafka dependency while allowing easy
    production upgrade to `confluent-kafka`.
    """

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        if _HAVE_CONFLUENT:
            self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        else:
            self._producer = None

    def produce(self, topic: str, key: Optional[bytes], value: bytes, headers: Dict[str, str] | None = None) -> None:
        if self._producer is not None:
            self._producer.produce(topic, key=key, value=value, headers=headers)
        else:
            # Fallback for local/dev runs
            print(f"[kafka-fallback] topic={topic} key={key} bytes={len(value)}")

    def flush(self, timeout: int = 10) -> None:
        if self._producer is not None:
            self._producer.flush(timeout)
        else:
            return

    def close(self) -> None:
        self.flush()
