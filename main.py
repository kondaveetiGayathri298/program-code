from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timedelta
import random
import time
from typing import List, Dict, Optional
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import pandas as pd

# Initialize FastAPI app
app = FastAPI(title="Smart Shelf-to-Door System", version="1.0.0")

# Data Models
class ShelfSensor(BaseModel):
    shelf_id: str
    product_id: str
    product_name: str
    current_stock: int
    max_capacity: int
    location: str
    last_updated: datetime

class StockAlert(BaseModel):
    shelf_id: str
    product_name: str
    current_stock: int
    predicted_stockout_time: datetime
    urgency: str  # "low", "medium", "high", "critical"

class DeliveryRoute(BaseModel):
    route_id: str
    driver_id: str
    stops: List[Dict]
    estimated_duration: int
    status: str

class CustomerOrder(BaseModel):
    order_id: str
    customer_id: str
    products: List[Dict]
    delivery_address: str
    estimated_arrival: datetime
    status: str

# Global variables for real-time data
shelf_data = {}
active_connections = []
ml_model = None
scaler = None

# Database initialization
def init_database():
    conn = sqlite3.connect('s2d_system.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shelves (
            shelf_id TEXT PRIMARY KEY,
            product_id TEXT,
            product_name TEXT,
            current_stock INTEGER,
            max_capacity INTEGER,
            location TEXT,
            last_updated TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shelf_id TEXT,
            product_name TEXT,
            current_stock INTEGER,
            predicted_stockout_time TIMESTAMP,
            urgency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivery_routes (
            route_id TEXT PRIMARY KEY,
            driver_id TEXT,
            stops TEXT,
            estimated_duration INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            products TEXT,
            delivery_address TEXT,
            estimated_arrival TIMESTAMP,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data
    sample_shelves = [
        ('SHELF_001', 'MILK_001', 'Organic Milk 1L', 25, 50, 'Dairy Section A1'),
        ('SHELF_002', 'BREAD_001', 'Whole Wheat Bread', 12, 30, 'Bakery Section B2'),
        ('SHELF_003', 'APPLE_001', 'Red Apples', 8, 40, 'Produce Section C1'),
        ('SHELF_004', 'WATER_001', 'Bottled Water 500ml', 35, 60, 'Beverages Section D1'),
        ('SHELF_005', 'CHIPS_001', 'Potato Chips', 18, 25, 'Snacks Section E1')
    ]
    
    for shelf in sample_shelves:
        cursor.execute('''
            INSERT OR REPLACE INTO shelves 
            (shelf_id, product_id, product_name, current_stock, max_capacity, location, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (*shelf, datetime.now()))
    
    conn.commit()
    conn.close()

# AI Demand Prediction Model
class DemandPredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train_model(self):
        # Generate synthetic training data
        np.random.seed(42)
        
        # Features: hour_of_day, day_of_week, current_stock, weather_score, event_factor
        X = []
        y = []
        
        for _ in range(1000):
            hour = random.randint(0, 23)
            day_of_week = random.randint(0, 6)
            current_stock = random.randint(5, 50)
            weather_score = random.uniform(0.5, 1.0)  # 1.0 = good weather
            event_factor = random.uniform(0.8, 1.5)   # 1.5 = special event
            
            # Simulate demand based on realistic patterns
            base_demand = 2 if hour < 8 or hour > 20 else 8
            if hour >= 17 and hour <= 19:  # Peak hours
                base_demand *= 1.5
            if day_of_week >= 5:  # Weekend
                base_demand *= 1.3
            
            demand = base_demand * weather_score * event_factor + np.random.normal(0, 1)
            demand = max(0, demand)
            
            X.append([hour, day_of_week, current_stock, weather_score, event_factor])
            y.append(demand)
        
        X = np.array(X)
        y = np.array(y)
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        print("AI Demand Prediction Model trained successfully!")
    
    def predict_demand(self, hour, day_of_week, current_stock, weather_score=1.0, event_factor=1.0):
        if not self.is_trained:
            self.train_model()
        
        features = np.array([[hour, day_of_week, current_stock, weather_score, event_factor]])
        features_scaled = self.scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]
        return max(0, prediction)
    
    def predict_stockout_time(self, current_stock, product_name):
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        # Predict hourly demand for next 24 hours
        remaining_stock = current_stock
        hours_ahead = 0
        
        while remaining_stock > 0 and hours_ahead < 48:
            hour = (current_hour + hours_ahead) % 24
            day = (current_day + (current_hour + hours_ahead) // 24) % 7
            
            predicted_demand = self.predict_demand(hour, day, remaining_stock)
            remaining_stock -= predicted_demand
            hours_ahead += 1
        
        if remaining_stock <= 0:
            stockout_time = datetime.now() + timedelta(hours=hours_ahead)
            return stockout_time
        
        return None  # No stockout predicted in next 48 hours

# Route Optimization
class RouteOptimizer:
    def __init__(self):
        self.store_locations = {
            'STORE_001': {'lat': 40.7128, 'lng': -74.0060, 'name': 'Manhattan Store'},
            'STORE_002': {'lat': 40.7589, 'lng': -73.9851, 'name': 'Times Square Store'},
            'STORE_003': {'lat': 40.6892, 'lng': -74.0445, 'name': 'Brooklyn Store'}
        }
    
    def calculate_distance(self, lat1, lng1, lat2, lng2):
        # Simplified distance calculation (Haversine formula approximation)
        dlat = abs(lat2 - lat1)
        dlng = abs(lng2 - lng1)
        return (dlat ** 2 + dlng ** 2) ** 0.5 * 111  # Rough km conversion
    
    def optimize_route(self, delivery_requests):
        # Simple nearest neighbor algorithm
        if not delivery_requests:
            return []
        
        # Start from warehouse
        current_location = {'lat': 40.7128, 'lng': -74.0060}
        route = []
        remaining_requests = delivery_requests.copy()
        
        while remaining_requests:
            nearest_request = min(remaining_requests, 
                                key=lambda req: self.calculate_distance(
                                    current_location['lat'], current_location['lng'],
                                    req['lat'], req['lng']
                                ))
            
            route.append(nearest_request)
            current_location = nearest_request
            remaining_requests.remove(nearest_request)
        
        return route

# Initialize components
demand_predictor = DemandPredictor()
route_optimizer = RouteOptimizer()

# IoT Sensor Simulation
class IoTSimulator:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start_simulation(self):
        self.running = True
        self.thread = threading.Thread(target=self._simulate_sensors)
        self.thread.start()
    
    def stop_simulation(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _simulate_sensors(self):
        while self.running:
            # Simulate stock changes
            conn = sqlite3.connect('s2d_system.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM shelves')
            shelves = cursor.fetchall()
            
            for shelf in shelves:
                shelf_id, product_id, product_name, current_stock, max_capacity, location, _ = shelf
                
                # Simulate stock depletion based on time of day
                current_hour = datetime.now().hour
                if 9 <= current_hour <= 21:  # Store hours
                    # Random stock decrease (simulating purchases)
                    if random.random() < 0.3:  # 30% chance of purchase
                        stock_decrease = random.randint(1, 3)
                        new_stock = max(0, current_stock - stock_decrease)
                        
                        cursor.execute('''
                            UPDATE shelves SET current_stock = ?, last_updated = ?
                            WHERE shelf_id = ?
                        ''', (new_stock, datetime.now(), shelf_id))
                        
                        # Update global shelf data
                        shelf_data[shelf_id] = {
                            'shelf_id': shelf_id,
                            'product_name': product_name,
                            'current_stock': new_stock,
                            'max_capacity': max_capacity,
                            'location': location,
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        # Check if restock alert is needed
                        if new_stock <= max_capacity * 0.2:  # 20% threshold
                            self._generate_stock_alert(shelf_id, product_name, new_stock)
            
            conn.commit()
            conn.close()
            
            # Broadcast updates to connected clients
            asyncio.run(self._broadcast_updates())
            
            time.sleep(5)  # Update every 5 seconds
    
    def _generate_stock_alert(self, shelf_id, product_name, current_stock):
        # Predict stockout time using AI
        stockout_time = demand_predictor.predict_stockout_time(current_stock, product_name)
        
        if stockout_time:
            hours_until_stockout = (stockout_time - datetime.now()).total_seconds() / 3600
            
            if hours_until_stockout <= 1:
                urgency = "critical"
            elif hours_until_stockout <= 3:
                urgency = "high"
            elif hours_until_stockout <= 6:
                urgency = "medium"
            else:
                urgency = "low"
            
            # Save alert to database
            conn = sqlite3.connect('s2d_system.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO stock_alerts 
                (shelf_id, product_name, current_stock, predicted_stockout_time, urgency)
                VALUES (?, ?, ?, ?, ?)
            ''', (shelf_id, product_name, current_stock, stockout_time, urgency))
            conn.commit()
            conn.close()
    
    async def _broadcast_updates(self):
        if active_connections:
            message = {
                'type': 'shelf_update',
                'data': shelf_data
            }
            
            disconnected = []
            for websocket in active_connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
            
            # Remove disconnected clients
            for ws in disconnected:
                if ws in active_connections:
                    active_connections.remove(ws)

# Initialize IoT simulator
iot_simulator = IoTSimulator()

# API Endpoints
@app.on_event("startup")
async def startup_event():
    init_database()
    demand_predictor.train_model()
    iot_simulator.start_simulation()

@app.on_event("shutdown")
async def shutdown_event():
    iot_simulator.stop_simulation()

@app.get("/")
async def root():
    return FileResponse('static/dashboard.html')

@app.get("/api/shelves")
async def get_shelves():
    conn = sqlite3.connect('s2d_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shelves')
    shelves = cursor.fetchall()
    conn.close()
    
    return [
        {
            'shelf_id': shelf[0],
            'product_id': shelf[1],
            'product_name': shelf[2],
            'current_stock': shelf[3],
            'max_capacity': shelf[4],
            'location': shelf[5],
            'last_updated': shelf[6],
            'stock_percentage': (shelf[3] / shelf[4]) * 100 if shelf[4] > 0 else 0
        }
        for shelf in shelves
    ]

@app.get("/api/alerts")
async def get_alerts():
    conn = sqlite3.connect('s2d_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM stock_alerts 
        ORDER BY created_at DESC 
        LIMIT 10
    ''')
    alerts = cursor.fetchall()
    conn.close()
    
    return [
        {
            'alert_id': alert[0],
            'shelf_id': alert[1],
            'product_name': alert[2],
            'current_stock': alert[3],
            'predicted_stockout_time': alert[4],
            'urgency': alert[5],
            'created_at': alert[6]
        }
        for alert in alerts
    ]

@app.get("/api/predict-demand/{shelf_id}")
async def predict_demand(shelf_id: str):
    conn = sqlite3.connect('s2d_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shelves WHERE shelf_id = ?', (shelf_id,))
    shelf = cursor.fetchone()
    conn.close()
    
    if not shelf:
        return {"error": "Shelf not found"}
    
    current_stock = shelf[3]
    product_name = shelf[2]
    
    # Predict next 24 hours
    predictions = []
    current_time = datetime.now()
    
    for hour_offset in range(0, 24):
        prediction_time = current_time + timedelta(hours=hour_offset)
        hour = prediction_time.hour
        day_of_week = prediction_time.weekday()
        
        predicted_demand = demand_predictor.predict_demand(
            hour, day_of_week, current_stock
        )
        
        predictions.append({
            'time': prediction_time.isoformat(),
            'predicted_demand': round(predicted_demand, 2)
        })
    
    stockout_time = demand_predictor.predict_stockout_time(current_stock, product_name)
    
    return {
        'shelf_id': shelf_id,
        'current_stock': current_stock,
        'predictions': predictions,
        'predicted_stockout_time': stockout_time.isoformat() if stockout_time else None
    }

@app.post("/api/generate-route")
async def generate_route(delivery_requests: List[Dict]):
    optimized_route = route_optimizer.optimize_route(delivery_requests)
    
    # Calculate total distance and estimated time
    total_distance = 0
    current_location = {'lat': 40.7128, 'lng': -74.0060}  # Warehouse
    
    for stop in optimized_route:
        distance = route_optimizer.calculate_distance(
            current_location['lat'], current_location['lng'],
            stop['lat'], stop['lng']
        )
        total_distance += distance
        current_location = stop
    
    estimated_duration = int(total_distance * 2.5)  # Assuming 2.5 minutes per km
    
    route_id = f"ROUTE_{int(time.time())}"
    
    # Save route to database
    conn = sqlite3.connect('s2d_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO delivery_routes 
        (route_id, driver_id, stops, estimated_duration, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (route_id, "DRIVER_001", json.dumps(optimized_route), estimated_duration, "planned"))
    conn.commit()
    conn.close()
    
    return {
        'route_id': route_id,
        'optimized_route': optimized_route,
        'total_distance_km': round(total_distance, 2),
        'estimated_duration_minutes': estimated_duration
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)