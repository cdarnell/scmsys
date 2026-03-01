import time
import json
from typing import Any, Iterable

from config import Settings
from api.auth import get_access_token
from api.client import TeslaClient
from kafka.producer import KafkaProducerWrapper
from logging_config import configure_logging, logger

try:
    from prometheus_client import start_http_server
    from prometheus_client import Counter
    _HAVE_PROM = True
except Exception:
    _HAVE_PROM = False


POLL_COUNTER = Counter("tesla_polls_total", "Number of poll cycles") if _HAVE_PROM else None
PRODUCE_COUNTER = Counter("tesla_produces_total", "Number of produced messages") if _HAVE_PROM else None
ERROR_COUNTER = Counter("tesla_errors_total", "Number of polling errors") if _HAVE_PROM else None


def poll_once(settings: Settings, client: TeslaClient, producer: KafkaProducerWrapper) -> None:
    """Perform a single poll and produce messages for all vehicles.

    Extracted for ease of testing.
    """
    vehicles = client.get_vehicles()

    # Support both raw list and TESLA response wrapper
    items: Iterable[Any]
    if isinstance(vehicles, dict) and "response" in vehicles:
        items = vehicles["response"]
    elif isinstance(vehicles, list):
        items = vehicles
    else:
        items = [vehicles]

    for v in items:
        try:
            key = None
            # Prefer VIN if available
            vid = None
            if isinstance(v, dict):
                vid = v.get("id") or v.get("vehicle_id") or v.get("vin")
                vin = v.get("vin")
                if vin:
                    key = str(vin).encode("utf-8")
            if key is None and vid is not None:
                key = str(vid).encode("utf-8")

            payload = {"vehicle": v, "ts": int(time.time())}
            payload_bytes = json.dumps(payload).encode("utf-8")
            producer.produce(settings.KAFKA_TOPIC, key=key, value=payload_bytes)
            if PRODUCE_COUNTER:
                PRODUCE_COUNTER.inc()
        except Exception:
            logger.exception("Failed producing vehicle payload")


def run_polling(settings: Settings, client: TeslaClient | None = None, producer: KafkaProducerWrapper | None = None) -> None:
    """Main polling loop.

    Accepts optional `client` and `producer` for easier testing and DI.
    """
    configure_logging()
    logger.info("Starting polling loop")

    if _HAVE_PROM and settings.PROMETHEUS_PORT:
        try:
            start_http_server(settings.PROMETHEUS_PORT)
            logger.info("Prometheus metrics available on port %s", settings.PROMETHEUS_PORT)
        except Exception:
            logger.exception("Failed to start Prometheus server")

    try:
        if client is None:
            token = get_access_token()
            client = TeslaClient(token)
    except NotImplementedError:
        logger.warning("No auth implemented; aborting polling loop")
        return

    if producer is None:
        producer = KafkaProducerWrapper(settings.KAFKA_BOOTSTRAP_SERVERS)

    interval = settings.TESLA_POLL_INTERVAL

    while True:
        try:
            if POLL_COUNTER:
                POLL_COUNTER.inc()
            poll_once(settings, client, producer)
            producer.flush()
            logger.info("Polled vehicles and produced to Kafka")
        except Exception as exc:
            logger.exception("Polling error: %s", exc)
            if ERROR_COUNTER:
                ERROR_COUNTER.inc()

        time.sleep(interval)
