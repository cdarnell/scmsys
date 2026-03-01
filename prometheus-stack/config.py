from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    TESLA_CLIENT_ID: str = ""
    TESLA_CLIENT_SECRET: str = ""
    TESLA_ACCESS_TOKEN: str = ""
    TESLA_POLL_INTERVAL: int = 30
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC: str = "tesla.telemetry"
    PROMETHEUS_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
    )
