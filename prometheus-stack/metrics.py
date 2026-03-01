"""Prometheus metrics for Tesla Fleet API telemetry."""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry
import time

# Create registry for all metrics
REGISTRY = CollectorRegistry()

# Vehicle metrics
vehicles_total = Gauge(
    'tesla_vehicles_total',
    'Total number of vehicles on account',
    registry=REGISTRY
)

vehicle_state = Gauge(
    'tesla_vehicle_state',
    'Vehicle state (online=1, offline=0)',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_battery_level = Gauge(
    'tesla_vehicle_battery_level',
    'Vehicle battery level percentage',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_estimated_range = Gauge(
    'tesla_vehicle_estimated_range',
    'Vehicle estimated range in miles',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_charge_state = Gauge(
    'tesla_vehicle_charge_state',
    'Vehicle charging state (charging=1, not_charging=0)',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_latitude = Gauge(
    'tesla_vehicle_latitude',
    'Vehicle latitude',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_longitude = Gauge(
    'tesla_vehicle_longitude',
    'Vehicle longitude',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_odometer = Gauge(
    'tesla_vehicle_odometer_miles',
    'Vehicle odometer in miles',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_signal_strength = Gauge(
    'tesla_vehicle_signal_strength',
    'Vehicle cellular signal strength (bars 0-5)',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_power = Gauge(
    'tesla_vehicle_power_kw',
    'Vehicle power in kilowatts (positive=charging, negative=discharging)',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

vehicle_inside_temp = Gauge(
    'tesla_vehicle_inside_temp_celsius',
    'Vehicle interior temperature in Celsius',
    labelnames=['vehicle_id', 'display_name', 'vin'],
    registry=REGISTRY
)

# API metrics
api_requests_total = Counter(
    'tesla_api_requests_total',
    'Total number of API requests',
    labelnames=['endpoint', 'status'],
    registry=REGISTRY
)

api_request_duration = Histogram(
    'tesla_api_request_duration_seconds',
    'API request duration in seconds',
    labelnames=['endpoint'],
    registry=REGISTRY
)

api_errors_total = Counter(
    'tesla_api_errors_total',
    'Total number of API errors',
    labelnames=['endpoint', 'error_type'],
    registry=REGISTRY
)

api_quota_daily = Gauge(
    'tesla_api_quota_daily_limit',
    'Daily API request quota limit',
    registry=REGISTRY
)

api_quota_used_daily = Gauge(
    'tesla_api_quota_daily_used',
    'Daily API requests used',
    registry=REGISTRY
)

api_quota_remaining = Gauge(
    'tesla_api_quota_remaining',
    'Remaining API requests for today',
    registry=REGISTRY
)

api_quota_percent_used = Gauge(
    'tesla_api_quota_percent_used',
    'Percentage of daily quota used',
    registry=REGISTRY
)

app_collection_count = Counter(
    'tesla_app_collection_iterations_total',
    'Total number of collection iterations',
    registry=REGISTRY
)

app_vehicles_processed_total = Counter(
    'tesla_app_vehicles_processed_total',
    'Total number of vehicles processed across all collections',
    registry=REGISTRY
)

metrics_collection_duration = Histogram(
    'tesla_metrics_collection_duration_seconds',
    'Time to collect all metrics in seconds',
    registry=REGISTRY
)

metrics_last_update = Gauge(
    'tesla_metrics_last_update_timestamp',
    'Unix timestamp of last metrics update',
    registry=REGISTRY
)


def update_vehicle_metrics(vehicle_data, vehicle_state_data=None):
    """Update metrics from vehicle data."""
    vehicle_id = str(vehicle_data.get('id'))
    display_name = vehicle_data.get('display_name', 'Unknown')
    vin = vehicle_data.get('vin', 'Unknown')
    
    labels = {'vehicle_id': vehicle_id, 'display_name': display_name, 'vin': vin}
    
    # Basic vehicle info
    state_val = 1 if vehicle_data.get('state') == 'online' else 0
    vehicle_state.labels(**labels).set(state_val)
    
    # Vehicle state data (if provided)
    if vehicle_state_data:
        charge_state = vehicle_state_data.get('charge_state', {})
        drive_state = vehicle_state_data.get('drive_state', {})
        vehicle_state_obj = vehicle_state_data.get('vehicle_state', {})
        
        # Battery and charging info
        battery_level = charge_state.get('battery_level')
        if battery_level is not None:
            vehicle_battery_level.labels(**labels).set(battery_level)
        
        estimated_range = charge_state.get('est_battery_range')
        if estimated_range is not None:
            vehicle_estimated_range.labels(**labels).set(estimated_range)
        
        charging_state = charge_state.get('charging_state', 'Disconnected')
        charge_val = 1 if charging_state == 'Charging' else 0
        vehicle_charge_state.labels(**labels).set(charge_val)
        
        # Power (positive=charging, negative=discharging)
        power = charge_state.get('power')
        if power is not None:
            vehicle_power.labels(**labels).set(power)
        
        # Location
        latitude = drive_state.get('latitude')
        longitude = drive_state.get('longitude')
        if latitude is not None:
            vehicle_latitude.labels(**labels).set(latitude)
        if longitude is not None:
            vehicle_longitude.labels(**labels).set(longitude)
        
        # Odometer
        odometer = vehicle_state_obj.get('odometer')
        if odometer is not None:
            vehicle_odometer.labels(**labels).set(odometer)
        
        # Signal strength (cellular bars)
        signal_bars = vehicle_state_obj.get('cell_gps_signal_bars')
        if signal_bars is not None:
            vehicle_signal_strength.labels(**labels).set(signal_bars)
        
        # Interior temperature
        inside_temp = vehicle_state_obj.get('interior_tempretatur')  # Note: typo in Tesla API
        if inside_temp is not None:
            vehicle_inside_temp.labels(**labels).set(inside_temp)


def record_api_request(endpoint, status, duration):
    """Record an API request."""
    api_requests_total.labels(endpoint=endpoint, status=status).inc()
    api_request_duration.labels(endpoint=endpoint).observe(duration)


def record_api_error(endpoint, error_type):
    """Record an API error."""
    api_errors_total.labels(endpoint=endpoint, error_type=error_type).inc()
