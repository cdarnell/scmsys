import time
from typing import Optional

from config import Settings
from api.auth import get_access_token
from api.client import TeslaClient
from kafka.producer import KafkaProducerWrapper
from polling.loop import poll_once
from logging_config import configure_logging, logger


class Collector:
    """Simple connector that pulls vehicle data and writes to Kafka.

    Keeps responsibilities intentionally small to stay testable and container-friendly.
    """

    def __init__(self, settings: Optional[Settings] = None):
        configure_logging()
        self.settings = settings or Settings()
        self.client: Optional[TeslaClient] = None
        self.producer: Optional[KafkaProducerWrapper] = None

    def init_clients(self) -> None:
        if self.client is None:
            self.client = TeslaClient()
        if self.producer is None:
            self.producer = KafkaProducerWrapper(self.settings.KAFKA_BOOTSTRAP_SERVERS)

    def run_once(self) -> None:
        self.init_clients()
        assert self.client is not None and self.producer is not None
        poll_once(self.settings, self.client, self.producer)
        self.producer.flush()

    def run_forever(self) -> None:
        self.init_clients()
        assert self.client is not None and self.producer is not None
        interval = self.settings.TESLA_POLL_INTERVAL
        while True:
            try:
                poll_once(self.settings, self.client, self.producer)
                self.producer.flush()
                logger.info("Collector cycle complete, sleeping %s seconds", interval)
            except Exception:
                logger.exception("Collector encountered an error")
            time.sleep(interval)
