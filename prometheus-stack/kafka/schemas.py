"""Schema definitions for messages (Avro/Protobuf) - placeholders."""

VEHICLE_TELEMETRY_SCHEMA = {
    "name": "vehicle_telemetry",
    "type": "record",
    "fields": [
        {"name": "vehicle_id", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "payload", "type": "string"},
    ],
}
