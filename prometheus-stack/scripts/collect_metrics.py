"""Tesla telemetry metrics collector service."""

import os
import time
import logging
import signal
import sys
from datetime import datetime
from threading import Thread

import requests
from prometheus_client import start_http_server, CollectorRegistry

from api.client import TeslaClient
from api.auth import get_access_token
from metrics import (
    REGISTRY,
    vehicles_total,
    update_vehicle_metrics,
    record_api_request,
    record_api_error,
    metrics_collection_duration,
    metrics_last_update,
    app_collection_count,
    app_vehicles_processed_total,
    api_quota_daily,
    api_quota_used_daily,
    api_quota_remaining,
    api_quota_percent_used,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '60'))  # seconds
METRICS_PORT = int(os.getenv('METRICS_PORT', '8000'))
FLEET_API_BASE = 'https://fleet-api.prd.na.vn.cloud.tesla.com/api/1'


class MetricsCollector:
    """Collects Tesla vehicle metrics and exposes them for Prometheus."""
    
    def __init__(self):
        self.running = True
        self.client = TeslaClient()
        
    def collect_vehicle_data(self, vehicle_id):
        """Collect detailed data for a single vehicle."""
        try:
            endpoint = f'/vehicles/{vehicle_id}/vehicle_data'
            url = f'{FLEET_API_BASE}{endpoint}'
            
            start_time = time.time()
            headers = {
                'Authorization': f'Bearer {get_access_token()}',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                record_api_request(endpoint, response.status_code, duration)
                return response.json().get('response')
            else:
                record_api_request(endpoint, response.status_code, duration)
                logger.error(f"Failed to fetch vehicle data: {response.status_code}")
                record_api_error(endpoint, f"HTTP_{response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error collecting vehicle data: {e}")
            record_api_error(endpoint, type(e).__name__)
            return None
    
    def collect_metrics(self):
        """Collect metrics from all vehicles."""
        try:
            collection_start = time.time()
            logger.info("Starting metrics collection...")
            
            # Increment collection counter
            app_collection_count.inc()
            
            # Get vehicles list
            vehicles = self.client.get_vehicles()
            if not vehicles:
                logger.warning("No vehicles found")
                return
            
            vehicles_list = vehicles.get('response', [])
            vehicles_total.set(len(vehicles_list))
            logger.info(f"Found {len(vehicles_list)} vehicle(s)")
            
            # Collect data for each vehicle
            for vehicle in vehicles_list:
                vehicle_id = vehicle.get('id')
                display_name = vehicle.get('display_name', 'Unknown')
                
                logger.info(f"Collecting data for {display_name} (ID: {vehicle_id})")
                
                # Update basic metrics
                update_vehicle_metrics(vehicle)
                
                # Collect detailed vehicle data
                vehicle_data = self.collect_vehicle_data(vehicle_id)
                if vehicle_data:
                    update_vehicle_metrics(vehicle, vehicle_data)
                    app_vehicles_processed_total.inc()
                    
                    # Log some interesting data
                    battery = vehicle_data.get('charge_state', {}).get('battery_level')
                    state = vehicle_data.get('drive_state', {})
                    odometer = vehicle_data.get('vehicle_state', {}).get('odometer')
                    signal_bars = vehicle_data.get('vehicle_state', {}).get('cell_gps_signal_bars')
                    
                    if battery is not None:
                        logger.info(f"  Battery: {battery}%")
                    if odometer is not None:
                        logger.info(f"  Odometer: {odometer:.1f} miles")
                    if signal_bars is not None:
                        logger.info(f"  Signal Strength: {signal_bars} bars")
            
            # Update API quota metrics (example values - you may need to fetch from actual API)
            # Tesla Fleet API typically has rate limits - we'll track our usage
            estimated_daily_limit = 10000  # Tesla's typical limit
            try:
                # Calculate quota usage based on collection count
                total_requests = app_collection_count._value.get() or 0
                vehicles_count = len(vehicles_list) if vehicles_list else 0
                
                # Each collection makes requests for: vehicles list + vehicle_data for each vehicle
                # Plus any additional API calls
                estimated_used = (total_requests * (1 + vehicles_count)) if total_requests > 0 else 0
                estimated_remaining = max(0, estimated_daily_limit - estimated_used)
                estimated_percent = (estimated_used / estimated_daily_limit * 100) if estimated_daily_limit > 0 else 0
                
                api_quota_daily.set(estimated_daily_limit)
                api_quota_used_daily.set(estimated_used)
                api_quota_remaining.set(estimated_remaining)
                api_quota_percent_used.set(estimated_percent)
                
                logger.info(f"Estimated API Quota - Used: {estimated_used}/{estimated_daily_limit} ({estimated_percent:.1f}%)")
            except Exception as e:
                logger.warning(f"Could not update quota metrics: {e}")
            
            # Record collection metrics
            duration = time.time() - collection_start
            metrics_collection_duration.observe(duration)
            metrics_last_update.set(time.time())
            
            logger.info(f"Metrics collection completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during metrics collection: {e}")
    
    def run_collection_loop(self):
        """Run the metrics collection loop."""
        logger.info(f"Starting metrics collection loop (interval: {COLLECTION_INTERVAL}s)")
        
        while self.running:
            try:
                self.collect_metrics()
                
                # Wait for next collection
                for _ in range(COLLECTION_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Collection loop interrupted")
                break
            except Exception as e:
                logger.error(f"Unexpected error in collection loop: {e}")
                # Wait before retrying
                time.sleep(5)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Tesla Metrics Collector")
    logger.info("=" * 60)
    
    # Start Prometheus HTTP server
    logger.info(f"Starting Prometheus metrics server on port {METRICS_PORT}")
    start_http_server(METRICS_PORT, registry=REGISTRY)
    logger.info(f"Metrics available at http://localhost:{METRICS_PORT}/metrics")
    
    # Create and run collector
    collector = MetricsCollector()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, collector.signal_handler)
    signal.signal(signal.SIGTERM, collector.signal_handler)
    
    # Do an initial collection
    logger.info("Performing initial metrics collection...")
    collector.collect_metrics()
    
    # Run collection loop
    collector.run_collection_loop()


if __name__ == '__main__':
    main()
