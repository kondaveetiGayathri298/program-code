#!/usr/bin/env python3
"""
IoT Sensors Module for Smart Shelf-to-Door System
Simulates various IoT sensors including RFID, weight sensors, and environmental sensors
"""

import random
import time
import json
import sqlite3
import threading
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional
import asyncio

class RFIDSensor:
    """Simulates RFID sensor for product identification"""
    
    def __init__(self, sensor_id: str, shelf_id: str):
        self.sensor_id = sensor_id
        self.shelf_id = shelf_id
        self.last_scan_time = datetime.now()
        self.products_in_range = []
    
    def scan_products(self) -> List[Dict]:
        """Simulate RFID scanning of products"""
        # Simulate random product detections
        product_templates = [
            {"product_id": "MILK_001", "name": "Organic Milk 1L", "price": 4.99},
            {"product_id": "BREAD_001", "name": "Whole Wheat Bread", "price": 2.49},
            {"product_id": "APPLE_001", "name": "Red Apples", "price": 3.99},
            {"product_id": "WATER_001", "name": "Bottled Water 500ml", "price": 1.99},
            {"product_id": "CHIPS_001", "name": "Potato Chips", "price": 2.99}
        ]
        
        # Randomly detect 0-3 products
        num_products = random.randint(0, 3)
        detected_products = random.sample(product_templates, min(num_products, len(product_templates)))
        
        for product in detected_products:
            product.update({
                "detected_at": datetime.now().isoformat(),
                "signal_strength": random.randint(60, 100),
                "shelf_id": self.shelf_id
            })
        
        self.products_in_range = detected_products
        self.last_scan_time = datetime.now()
        
        return detected_products

class WeightSensor:
    """Simulates load cell weight sensor for shelf monitoring"""
    
    def __init__(self, sensor_id: str, shelf_id: str, max_weight: float = 50.0):
        self.sensor_id = sensor_id
        self.shelf_id = shelf_id
        self.max_weight = max_weight  # kg
        self.current_weight = random.uniform(10.0, max_weight)
        self.baseline_weight = 2.0  # Empty shelf weight
        self.last_reading_time = datetime.now()
    
    def get_weight_reading(self) -> Dict:
        """Get current weight reading with noise simulation"""
        # Add some realistic noise and drift
        noise = random.uniform(-0.1, 0.1)
        drift = random.uniform(-0.05, 0.05)
        
        # Simulate weight changes (product removal/addition)
        if random.random() < 0.1:  # 10% chance of weight change
            weight_change = random.uniform(-2.0, 1.0)  # More likely to decrease (purchases)
            self.current_weight = max(self.baseline_weight, 
                                    min(self.max_weight, self.current_weight + weight_change))
        
        measured_weight = self.current_weight + noise + drift
        
        # Estimate product count based on average product weight
        avg_product_weight = 0.5  # kg
        estimated_products = max(0, int((measured_weight - self.baseline_weight) / avg_product_weight))
        
        self.last_reading_time = datetime.now()
        
        return {
            "sensor_id": self.sensor_id,
            "shelf_id": self.shelf_id,
            "weight_kg": round(measured_weight, 2),
            "estimated_products": estimated_products,
            "timestamp": self.last_reading_time.isoformat(),
            "sensor_status": "online"
        }

class EnvironmentalSensor:
    """Simulates temperature and humidity sensors"""
    
    def __init__(self, sensor_id: str, location: str):
        self.sensor_id = sensor_id
        self.location = location
        self.temperature = random.uniform(18.0, 24.0)  # Celsius
        self.humidity = random.uniform(40.0, 60.0)      # Percentage
    
    def get_reading(self) -> Dict:
        """Get environmental readings"""
        # Simulate gradual changes
        temp_change = random.uniform(-0.5, 0.5)
        humidity_change = random.uniform(-2.0, 2.0)
        
        self.temperature += temp_change
        self.humidity += humidity_change
        
        # Keep within realistic bounds
        self.temperature = max(15.0, min(30.0, self.temperature))
        self.humidity = max(30.0, min(80.0, self.humidity))
        
        return {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "temperature_c": round(self.temperature, 1),
            "humidity_percent": round(self.humidity, 1),
            "timestamp": datetime.now().isoformat(),
            "status": "normal" if 18 <= self.temperature <= 25 and 40 <= self.humidity <= 65 else "warning"
        }

class SmartShelfHub:
    """Central hub that manages all sensors for a smart shelf"""
    
    def __init__(self, shelf_id: str, location: str, api_endpoint: str = "http://localhost:8000"):
        self.shelf_id = shelf_id
        self.location = location
        self.api_endpoint = api_endpoint
        
        # Initialize sensors
        self.rfid_sensor = RFIDSensor(f"RFID_{shelf_id}", shelf_id)
        self.weight_sensor = WeightSensor(f"WEIGHT_{shelf_id}", shelf_id)
        self.env_sensor = EnvironmentalSensor(f"ENV_{shelf_id}", location)
        
        self.is_running = False
        self.data_buffer = []
        self.last_sync_time = datetime.now()
    
    def collect_sensor_data(self) -> Dict:
        """Collect data from all sensors"""
        return {
            "shelf_id": self.shelf_id,
            "location": self.location,
            "timestamp": datetime.now().isoformat(),
            "rfid_data": self.rfid_sensor.scan_products(),
            "weight_data": self.weight_sensor.get_weight_reading(),
            "environmental_data": self.env_sensor.get_reading(),
            "hub_status": "online"
        }
    
    def sync_to_cloud(self, data: Dict) -> bool:
        """Send sensor data to cloud API"""
        try:
            response = requests.post(
                f"{self.api_endpoint}/api/sensor-data",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Failed to sync data for {self.shelf_id}: {e}")
            return False
    
    def run_continuous_monitoring(self, interval: int = 5):
        """Run continuous sensor monitoring"""
        self.is_running = True
        print(f"Starting continuous monitoring for shelf {self.shelf_id}")
        
        while self.is_running:
            try:
                # Collect sensor data
                sensor_data = self.collect_sensor_data()
                self.data_buffer.append(sensor_data)
                
                # Update local database
                self.update_local_database(sensor_data)
                
                # Sync to cloud every 30 seconds or when buffer is full
                if (datetime.now() - self.last_sync_time).seconds >= 30 or len(self.data_buffer) >= 10:
                    self.sync_buffered_data()
                
                # Print status
                weight_data = sensor_data["weight_data"]
                env_data = sensor_data["environmental_data"]
                print(f"[{self.shelf_id}] Weight: {weight_data['weight_kg']}kg, "
                      f"Products: {weight_data['estimated_products']}, "
                      f"Temp: {env_data['temperature_c']}°C")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print(f"Stopping monitoring for shelf {self.shelf_id}")
                break
            except Exception as e:
                print(f"Error in monitoring loop for {self.shelf_id}: {e}")
                time.sleep(interval)
        
        self.is_running = False
    
    def update_local_database(self, sensor_data: Dict):
        """Update local SQLite database with sensor data"""
        try:
            conn = sqlite3.connect('s2d_system.db')
            cursor = conn.cursor()
            
            # Update shelf stock based on weight sensor
            weight_data = sensor_data["weight_data"]
            estimated_stock = weight_data["estimated_products"]
            
            cursor.execute('''
                UPDATE shelves 
                SET current_stock = ?, last_updated = ?
                WHERE shelf_id = ?
            ''', (estimated_stock, datetime.now(), self.shelf_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database update error: {e}")
    
    def sync_buffered_data(self):
        """Sync all buffered data to cloud"""
        if not self.data_buffer:
            return
        
        for data in self.data_buffer:
            if self.sync_to_cloud(data):
                print(f"Synced data for {self.shelf_id}")
            else:
                print(f"Failed to sync data for {self.shelf_id}")
        
        self.data_buffer.clear()
        self.last_sync_time = datetime.now()
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False

class IoTNetworkSimulator:
    """Simulates an entire network of IoT-enabled smart shelves"""
    
    def __init__(self, api_endpoint: str = "http://localhost:8000"):
        self.api_endpoint = api_endpoint
        self.smart_shelves = {}
        self.monitoring_threads = {}
        
        # Initialize smart shelves
        shelf_configs = [
            ("SHELF_001", "Dairy Section A1"),
            ("SHELF_002", "Bakery Section B2"), 
            ("SHELF_003", "Produce Section C1"),
            ("SHELF_004", "Beverages Section D1"),
            ("SHELF_005", "Snacks Section E1")
        ]
        
        for shelf_id, location in shelf_configs:
            self.smart_shelves[shelf_id] = SmartShelfHub(shelf_id, location, api_endpoint)
    
    def start_all_monitoring(self, interval: int = 5):
        """Start monitoring for all smart shelves"""
        print("Starting IoT Network Simulation...")
        
        for shelf_id, shelf_hub in self.smart_shelves.items():
            thread = threading.Thread(
                target=shelf_hub.run_continuous_monitoring,
                args=(interval,),
                name=f"Monitor_{shelf_id}"
            )
            thread.daemon = True
            thread.start()
            self.monitoring_threads[shelf_id] = thread
            
            # Stagger startup to avoid overwhelming the system
            time.sleep(1)
        
        print(f"Started monitoring for {len(self.smart_shelves)} smart shelves")
    
    def stop_all_monitoring(self):
        """Stop monitoring for all smart shelves"""
        print("Stopping IoT Network Simulation...")
        
        for shelf_hub in self.smart_shelves.values():
            shelf_hub.stop_monitoring()
        
        # Wait for threads to finish
        for thread in self.monitoring_threads.values():
            thread.join(timeout=5)
        
        print("IoT Network Simulation stopped")
    
    def get_network_status(self) -> Dict:
        """Get status of all shelves in the network"""
        status = {
            "total_shelves": len(self.smart_shelves),
            "active_shelves": sum(1 for shelf in self.smart_shelves.values() if shelf.is_running),
            "last_updated": datetime.now().isoformat(),
            "shelves": {}
        }
        
        for shelf_id, shelf_hub in self.smart_shelves.items():
            latest_data = shelf_hub.collect_sensor_data()
            status["shelves"][shelf_id] = {
                "location": shelf_hub.location,
                "status": "online" if shelf_hub.is_running else "offline",
                "last_weight_reading": latest_data["weight_data"]["weight_kg"],
                "estimated_products": latest_data["weight_data"]["estimated_products"],
                "temperature": latest_data["environmental_data"]["temperature_c"],
                "humidity": latest_data["environmental_data"]["humidity_percent"]
            }
        
        return status

# Advanced Analytics Module
class SensorAnalytics:
    """Analyze sensor data for insights and predictions"""
    
    def __init__(self, db_path: str = 's2d_system.db'):
        self.db_path = db_path
    
    def analyze_stock_patterns(self, shelf_id: str, days: int = 7) -> Dict:
        """Analyze stock depletion patterns"""
        # This would typically analyze historical sensor data
        # For simulation, we'll generate realistic patterns
        
        patterns = {
            "peak_hours": [9, 12, 17, 19],  # High activity hours
            "low_activity_hours": [2, 4, 6, 22],
            "weekend_multiplier": 1.3,
            "avg_depletion_rate": random.uniform(2.0, 8.0),  # units per hour
            "restocking_frequency": random.randint(1, 3),    # times per day
            "seasonal_factor": random.uniform(0.8, 1.2)
        }
        
        return {
            "shelf_id": shelf_id,
            "analysis_period_days": days,
            "patterns": patterns,
            "confidence_score": random.uniform(0.75, 0.95),
            "next_restock_prediction": (datetime.now() + timedelta(hours=random.randint(2, 12))).isoformat()
        }
    
    def detect_anomalies(self, shelf_id: str) -> List[Dict]:
        """Detect anomalies in sensor data"""
        anomalies = []
        
        # Simulate various types of anomalies
        anomaly_types = [
            {
                "type": "rapid_depletion",
                "description": "Stock depleting faster than expected",
                "severity": "medium",
                "confidence": 0.85
            },
            {
                "type": "sensor_drift",
                "description": "Weight sensor showing inconsistent readings",
                "severity": "low",
                "confidence": 0.72
            },
            {
                "type": "temperature_spike",
                "description": "Temperature readings above normal range",
                "severity": "high",
                "confidence": 0.91
            }
        ]
        
        # Randomly generate 0-2 anomalies
        num_anomalies = random.randint(0, 2)
        if num_anomalies > 0:
            selected_anomalies = random.sample(anomaly_types, num_anomalies)
            for anomaly in selected_anomalies:
                anomaly.update({
                    "shelf_id": shelf_id,
                    "detected_at": datetime.now().isoformat(),
                    "status": "active"
                })
                anomalies.append(anomaly)
        
        return anomalies

def main():
    """Main function to run the IoT simulation"""
    print("🚀 Starting Smart Shelf IoT Simulation")
    
    # Initialize the IoT network
    iot_network = IoTNetworkSimulator()
    
    try:
        # Start monitoring all shelves
        iot_network.start_all_monitoring(interval=3)
        
        # Run analytics periodically
        analytics = SensorAnalytics()
        
        # Keep the simulation running
        while True:
            time.sleep(30)
            
            # Print network status
            status = iot_network.get_network_status()
            print(f"\n📊 Network Status: {status['active_shelves']}/{status['total_shelves']} shelves active")
            
            # Run analytics on random shelf
            if status['active_shelves'] > 0:
                random_shelf = random.choice(list(status['shelves'].keys()))
                patterns = analytics.analyze_stock_patterns(random_shelf)
                anomalies = analytics.detect_anomalies(random_shelf)
                
                print(f"📈 Analysis for {random_shelf}: Confidence {patterns['confidence_score']:.2f}")
                if anomalies:
                    print(f"⚠️  Anomalies detected: {len(anomalies)}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping IoT simulation...")
        iot_network.stop_all_monitoring()
        print("IoT simulation stopped")

if __name__ == "__main__":
    main()