"""Simple metrics viewer for Tesla telemetry."""

import sys
import time
import requests
from collections import defaultdict


def fetch_metrics():
    """Fetch current metrics from Prometheus endpoint."""
    try:
        response = requests.get('http://localhost:8000/metrics', timeout=5)
        return response.text
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return None


def parse_metrics(metrics_text):
    """Parse Prometheus metrics text format."""
    metrics = defaultdict(dict)
    
    for line in metrics_text.split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        
        if '{' in line:
            # Parse metric with labels
            metric_name = line.split('{')[0]
            labels_part = line.split('{')[1].split('}')[0]
            value = line.split('} ')[1]
            
            labels = {}
            for label in labels_part.split(','):
                k, v = label.split('=')
                labels[k.strip()] = v.strip('"')
            
            metrics[metric_name] = {
                'labels': labels,
                'value': float(value)
            }
        else:
            # Parse metric without labels
            parts = line.split(' ')
            if len(parts) >= 2:
                metric_name = parts[0]
                value = parts[1]
                try:
                    metrics[metric_name] = {
                        'labels': {},
                        'value': float(value)
                    }
                except ValueError:
                    pass
    
    return metrics


def display_metrics():
    """Display formatted metrics."""
    print("\n" + "="*60)
    print("TESLA VEHICLE METRICS")
    print("="*60)
    
    metrics_text = fetch_metrics()
    if not metrics_text:
        return
    
    metrics = parse_metrics(metrics_text)
    
    # Display vehicle overview
    total = metrics.get('tesla_vehicles_total', {}).get('value', 0)
    print(f"\n📊 Total Vehicles: {int(total)}")
    
    # Display vehicle-specific metrics
    battery_metrics = {k: v for k, v in metrics.items() if 'battery_level' in k}
    odometer_metrics = {k: v for k, v in metrics.items() if 'odometer' in k}
    state_metrics = {k: v for k, v in metrics.items() if k == 'tesla_vehicle_state'}
    
    if battery_metrics:
        print("\n🔋 Battery Status:")
        for metric_name, data in battery_metrics.items():
            labels = data['labels']
            value = data['value']
            vehicle = labels.get('display_name', 'Unknown')
            vin = labels.get('vin', 'N/A')
            print(f"   {vehicle} ({vin}): {value:.1f}%")
    
    if odometer_metrics:
        print("\n🛣️  Odometer:")
        for metric_name, data in odometer_metrics.items():
            labels = data['labels']
            value = data['value']
            vehicle = labels.get('display_name', 'Unknown')
            vin = labels.get('vin', 'N/A')
            print(f"   {vehicle} ({vin}): {value:,.0f} miles")
    
    if state_metrics:
        print("\n🟢 Vehicle State:")
        for metric_name, data in state_metrics.items():
            labels = data['labels']
            value = data['value']
            vehicle = labels.get('display_name', 'Unknown')
            state_val = int(value)
            state = "Online" if state_val == 1 else "Offline"
            print(f"   {vehicle}: {state}")
    
    # Display collection stats
    collection_time = metrics.get('tesla_metrics_collection_duration_seconds_sum', {}).get('value', 0)
    last_update = metrics.get('tesla_metrics_last_update_timestamp', {}).get('value', 0)
    
    if last_update > 0:
        from datetime import datetime
        update_time = datetime.fromtimestamp(last_update).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n⏱️  Last Update: {update_time}")
    
    if collection_time > 0:
        print(f"⏱️  Collection Duration: {collection_time:.2f}s")
    
    # Display API metrics
    requests_total = metrics.get('tesla_api_requests_total_total', {}).get('value', 0)
    errors_total = metrics.get('tesla_api_errors_total_total', {}).get('value', 0)
    
    if requests_total > 0 or errors_total > 0:
        print(f"\n📈 API Statistics:")
        print(f"   Total Requests: {int(requests_total)}")
        if errors_total > 0:
            print(f"   Total Errors: {int(errors_total)}")
    
    print("\n" + "="*60)
    print("Metrics endpoint: http://localhost:8000/metrics")
    print("="*60 + "\n")


def main():
    """Main loop."""
    try:
        while True:
            display_metrics()
            print("Refreshing in 10 seconds (Ctrl+C to quit)...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == '__main__':
    main()
