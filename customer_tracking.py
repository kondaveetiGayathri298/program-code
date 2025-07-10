#!/usr/bin/env python3
"""
Customer Tracking Module for Smart Shelf-to-Door System
Handles real-time delivery tracking, SMS/WhatsApp notifications, and customer communication
"""

import random
import time
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import asyncio
from dataclasses import dataclass
from enum import Enum

class OrderStatus(Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class NotificationType(Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PUSH = "push"

@dataclass
class Customer:
    customer_id: str
    name: str
    phone: str
    email: str
    address: str
    lat: float
    lng: float
    preferred_notifications: List[NotificationType]

@dataclass
class DeliveryAgent:
    agent_id: str
    name: str
    phone: str
    vehicle_type: str
    current_lat: float
    current_lng: float
    status: str  # "available", "busy", "offline"
    current_orders: List[str]

@dataclass
class Order:
    order_id: str
    customer_id: str
    products: List[Dict]
    total_amount: float
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    status: OrderStatus
    estimated_delivery_time: datetime
    actual_delivery_time: Optional[datetime]
    delivery_agent_id: Optional[str]
    tracking_updates: List[Dict]

class GeolocationService:
    """Simulates GPS tracking for delivery agents"""
    
    def __init__(self):
        self.agent_locations = {}
    
    def update_agent_location(self, agent_id: str, lat: float, lng: float):
        """Update delivery agent's current location"""
        self.agent_locations[agent_id] = {
            "lat": lat,
            "lng": lng,
            "timestamp": datetime.now().isoformat(),
            "speed": random.uniform(15, 45)  # km/h
        }
    
    def get_agent_location(self, agent_id: str) -> Optional[Dict]:
        """Get current location of delivery agent"""
        return self.agent_locations.get(agent_id)
    
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points (simplified)"""
        dlat = abs(lat2 - lat1)
        dlng = abs(lng2 - lng1)
        return (dlat ** 2 + dlng ** 2) ** 0.5 * 111  # Rough km conversion
    
    def calculate_eta(self, agent_id: str, destination_lat: float, destination_lng: float) -> Optional[int]:
        """Calculate estimated time of arrival in minutes"""
        agent_location = self.get_agent_location(agent_id)
        if not agent_location:
            return None
        
        distance = self.calculate_distance(
            agent_location["lat"], agent_location["lng"],
            destination_lat, destination_lng
        )
        
        # Account for traffic and delivery time
        traffic_factor = random.uniform(1.2, 2.0)
        delivery_time = 5  # 5 minutes for delivery
        
        speed_kmh = agent_location.get("speed", 30)
        travel_time_hours = (distance * traffic_factor) / speed_kmh
        total_time_minutes = (travel_time_hours * 60) + delivery_time
        
        return int(total_time_minutes)

class NotificationService:
    """Handles SMS, WhatsApp, and other notification services"""
    
    def __init__(self):
        self.notification_log = []
        self.sms_api_key = "sim_sms_key_12345"
        self.whatsapp_api_key = "sim_wa_key_67890"
    
    def send_sms(self, phone: str, message: str) -> bool:
        """Simulate SMS sending"""
        try:
            # Simulate API call delay
            time.sleep(0.1)
            
            notification = {
                "type": "SMS",
                "phone": phone,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "status": "delivered" if random.random() > 0.05 else "failed",
                "cost": 0.05  # $0.05 per SMS
            }
            
            self.notification_log.append(notification)
            print(f"📱 SMS sent to {phone[:6]}******: {message[:50]}...")
            
            return notification["status"] == "delivered"
            
        except Exception as e:
            print(f"❌ SMS failed: {e}")
            return False
    
    def send_whatsapp(self, phone: str, message: str, media_url: Optional[str] = None) -> bool:
        """Simulate WhatsApp message sending"""
        try:
            # Simulate API call delay
            time.sleep(0.15)
            
            notification = {
                "type": "WhatsApp",
                "phone": phone,
                "message": message,
                "media_url": media_url,
                "sent_at": datetime.now().isoformat(),
                "status": "delivered" if random.random() > 0.02 else "failed",
                "cost": 0.02  # $0.02 per WhatsApp message
            }
            
            self.notification_log.append(notification)
            print(f"💬 WhatsApp sent to {phone[:6]}******: {message[:50]}...")
            
            return notification["status"] == "delivered"
            
        except Exception as e:
            print(f"❌ WhatsApp failed: {e}")
            return False
    
    def send_push_notification(self, customer_id: str, title: str, message: str) -> bool:
        """Simulate push notification"""
        try:
            notification = {
                "type": "Push",
                "customer_id": customer_id,
                "title": title,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "status": "delivered" if random.random() > 0.01 else "failed",
                "cost": 0.001  # $0.001 per push notification
            }
            
            self.notification_log.append(notification)
            print(f"🔔 Push notification sent to {customer_id}: {title}")
            
            return notification["status"] == "delivered"
            
        except Exception as e:
            print(f"❌ Push notification failed: {e}")
            return False

class OrderTrackingSystem:
    """Main system for tracking orders and managing deliveries"""
    
    def __init__(self, db_path: str = 's2d_system.db'):
        self.db_path = db_path
        self.geolocation = GeolocationService()
        self.notifications = NotificationService()
        
        # Sample data
        self.customers = self._initialize_customers()
        self.delivery_agents = self._initialize_delivery_agents()
        self.active_orders = {}
        
        self.tracking_thread = None
        self.is_running = False
    
    def _initialize_customers(self) -> Dict[str, Customer]:
        """Initialize sample customers"""
        customers = {}
        
        sample_customers = [
            ("CUST_001", "Alice Johnson", "+1234567890", "alice@email.com", "123 Main St, NYC", 40.7128, -74.0060),
            ("CUST_002", "Bob Smith", "+1234567891", "bob@email.com", "456 Oak Ave, NYC", 40.7589, -73.9851),
            ("CUST_003", "Carol Davis", "+1234567892", "carol@email.com", "789 Pine Rd, NYC", 40.6892, -74.0445),
            ("CUST_004", "David Wilson", "+1234567893", "david@email.com", "321 Elm St, NYC", 40.7410, -73.9896),
            ("CUST_005", "Eva Brown", "+1234567894", "eva@email.com", "654 Cedar Ln, NYC", 40.7831, -73.9712)
        ]
        
        for customer_data in sample_customers:
            customer = Customer(
                customer_id=customer_data[0],
                name=customer_data[1],
                phone=customer_data[2],
                email=customer_data[3],
                address=customer_data[4],
                lat=customer_data[5],
                lng=customer_data[6],
                preferred_notifications=[NotificationType.SMS, NotificationType.WHATSAPP]
            )
            customers[customer.customer_id] = customer
        
        return customers
    
    def _initialize_delivery_agents(self) -> Dict[str, DeliveryAgent]:
        """Initialize sample delivery agents"""
        agents = {}
        
        sample_agents = [
            ("AGENT_001", "Mike Rodriguez", "+1555000001", "motorcycle", 40.7128, -74.0060),
            ("AGENT_002", "Sarah Chen", "+1555000002", "bicycle", 40.7589, -73.9851),
            ("AGENT_003", "James Kim", "+1555000003", "van", 40.6892, -74.0445)
        ]
        
        for agent_data in sample_agents:
            agent = DeliveryAgent(
                agent_id=agent_data[0],
                name=agent_data[1],
                phone=agent_data[2],
                vehicle_type=agent_data[3],
                current_lat=agent_data[4],
                current_lng=agent_data[5],
                status="available",
                current_orders=[]
            )
            agents[agent.agent_id] = agent
            
            # Initialize location tracking
            self.geolocation.update_agent_location(
                agent.agent_id, agent.current_lat, agent.current_lng
            )
        
        return agents
    
    def create_order(self, customer_id: str, products: List[Dict], delivery_address: str = None) -> str:
        """Create a new order"""
        customer = self.customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        order_id = f"ORDER_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Calculate total amount
        total_amount = sum(product.get("price", 0) * product.get("quantity", 1) for product in products)
        
        # Use customer's address if no delivery address provided
        if not delivery_address:
            delivery_address = customer.address
            delivery_lat = customer.lat
            delivery_lng = customer.lng
        else:
            # For simulation, generate random coordinates near customer
            delivery_lat = customer.lat + random.uniform(-0.01, 0.01)
            delivery_lng = customer.lng + random.uniform(-0.01, 0.01)
        
        # Estimate delivery time (30 minutes to 2 hours from now)
        estimated_delivery = datetime.now() + timedelta(minutes=random.randint(30, 120))
        
        order = Order(
            order_id=order_id,
            customer_id=customer_id,
            products=products,
            total_amount=total_amount,
            delivery_address=delivery_address,
            delivery_lat=delivery_lat,
            delivery_lng=delivery_lng,
            status=OrderStatus.PLACED,
            estimated_delivery_time=estimated_delivery,
            actual_delivery_time=None,
            delivery_agent_id=None,
            tracking_updates=[]
        )
        
        self.active_orders[order_id] = order
        
        # Send order confirmation
        self._send_order_confirmation(order)
        
        # Auto-assign delivery agent
        self._assign_delivery_agent(order_id)
        
        return order_id
    
    def _send_order_confirmation(self, order: Order):
        """Send order confirmation to customer"""
        customer = self.customers[order.customer_id]
        
        message = f"🛒 Order confirmed! Order #{order.order_id[-8:]} - ${order.total_amount:.2f}\n" \
                 f"📦 {len(order.products)} items\n" \
                 f"🕒 Est. delivery: {order.estimated_delivery_time.strftime('%I:%M %p')}\n" \
                 f"📍 To: {order.delivery_address}\n" \
                 f"Track your order: http://tracking.s2d.com/{order.order_id}"
        
        # Send via preferred notification methods
        for notification_type in customer.preferred_notifications:
            if notification_type == NotificationType.SMS:
                self.notifications.send_sms(customer.phone, message)
            elif notification_type == NotificationType.WHATSAPP:
                self.notifications.send_whatsapp(customer.phone, message)
        
        # Also send push notification
        self.notifications.send_push_notification(
            customer.customer_id,
            "Order Confirmed!",
            f"Your order #{order.order_id[-8:]} has been confirmed"
        )
    
    def _assign_delivery_agent(self, order_id: str) -> bool:
        """Assign the best available delivery agent to an order"""
        order = self.active_orders.get(order_id)
        if not order:
            return False
        
        # Find available agents
        available_agents = [
            agent for agent in self.delivery_agents.values()
            if agent.status == "available" and len(agent.current_orders) < 3
        ]
        
        if not available_agents:
            print(f"⚠️ No available agents for order {order_id}")
            return False
        
        # Choose agent closest to delivery location
        best_agent = min(available_agents, key=lambda agent: 
                        self.geolocation.calculate_distance(
                            agent.current_lat, agent.current_lng,
                            order.delivery_lat, order.delivery_lng
                        ))
        
        # Assign the order
        order.delivery_agent_id = best_agent.agent_id
        order.status = OrderStatus.CONFIRMED
        best_agent.current_orders.append(order_id)
        best_agent.status = "busy"
        
        # Add tracking update
        self._add_tracking_update(order_id, "Order assigned to delivery agent", {
            "agent_name": best_agent.name,
            "vehicle_type": best_agent.vehicle_type
        })
        
        print(f"🚚 Order {order_id} assigned to {best_agent.name} ({best_agent.vehicle_type})")
        
        # Send assignment notification
        self._send_assignment_notification(order)
        
        return True
    
    def _add_tracking_update(self, order_id: str, message: str, extra_data: Dict = None):
        """Add a tracking update to an order"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        update = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "status": order.status.value,
            "extra_data": extra_data or {}
        }
        
        order.tracking_updates.append(update)
    
    def _send_assignment_notification(self, order: Order):
        """Send notification when delivery agent is assigned"""
        customer = self.customers[order.customer_id]
        agent = self.delivery_agents[order.delivery_agent_id]
        
        # Calculate ETA
        eta_minutes = self.geolocation.calculate_eta(
            agent.agent_id, order.delivery_lat, order.delivery_lng
        )
        eta_text = f"~{eta_minutes} minutes" if eta_minutes else "calculating..."
        
        message = f"🚚 Your order is being prepared!\n" \
                 f"📦 Order #{order.order_id[-8:]}\n" \
                 f"👨‍🚀 Driver: {agent.name} ({agent.vehicle_type})\n" \
                 f"🕒 ETA: {eta_text}\n" \
                 f"📞 Driver phone: {agent.phone}\n" \
                 f"Live tracking: http://track.s2d.com/{order.order_id}"
        
        # Send notifications
        for notification_type in customer.preferred_notifications:
            if notification_type == NotificationType.SMS:
                self.notifications.send_sms(customer.phone, message)
            elif notification_type == NotificationType.WHATSAPP:
                self.notifications.send_whatsapp(customer.phone, message)
    
    def update_order_status(self, order_id: str, new_status: OrderStatus, message: str = None):
        """Update order status and send notifications"""
        order = self.active_orders.get(order_id)
        if not order:
            return False
        
        old_status = order.status
        order.status = new_status
        
        if message:
            self._add_tracking_update(order_id, message)
        
        # Send status update notification
        self._send_status_update_notification(order, old_status)
        
        # Handle status-specific logic
        if new_status == OrderStatus.OUT_FOR_DELIVERY:
            self._start_live_tracking(order_id)
        elif new_status == OrderStatus.DELIVERED:
            order.actual_delivery_time = datetime.now()
            self._complete_delivery(order_id)
        
        return True
    
    def _send_status_update_notification(self, order: Order, old_status: OrderStatus):
        """Send notification for status updates"""
        customer = self.customers[order.customer_id]
        
        status_messages = {
            OrderStatus.PREPARING: "👨‍🍳 Your order is being prepared!",
            OrderStatus.OUT_FOR_DELIVERY: "🚚 Your order is out for delivery!",
            OrderStatus.DELIVERED: "✅ Your order has been delivered!"
        }
        
        if order.status in status_messages:
            base_message = status_messages[order.status]
            
            if order.status == OrderStatus.OUT_FOR_DELIVERY:
                agent = self.delivery_agents[order.delivery_agent_id]
                eta_minutes = self.geolocation.calculate_eta(
                    agent.agent_id, order.delivery_lat, order.delivery_lng
                )
                eta_text = f"~{eta_minutes} minutes" if eta_minutes else "soon"
                
                message = f"{base_message}\n" \
                         f"📦 Order #{order.order_id[-8:]}\n" \
                         f"🕒 ETA: {eta_text}\n" \
                         f"🗺️ Live tracking: http://track.s2d.com/{order.order_id}"
            else:
                message = f"{base_message}\n📦 Order #{order.order_id[-8:]}"
            
            # Send notifications
            for notification_type in customer.preferred_notifications:
                if notification_type == NotificationType.SMS:
                    self.notifications.send_sms(customer.phone, message)
                elif notification_type == NotificationType.WHATSAPP:
                    self.notifications.send_whatsapp(customer.phone, message)
    
    def _start_live_tracking(self, order_id: str):
        """Start live tracking for an order out for delivery"""
        order = self.active_orders.get(order_id)
        if not order or not order.delivery_agent_id:
            return
        
        print(f"📍 Started live tracking for order {order_id}")
        
        # Send initial location
        agent_location = self.geolocation.get_agent_location(order.delivery_agent_id)
        if agent_location:
            self._add_tracking_update(order_id, "Live tracking started", {
                "agent_location": agent_location,
                "tracking_url": f"http://track.s2d.com/{order_id}"
            })
    
    def _complete_delivery(self, order_id: str):
        """Complete delivery and cleanup"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        # Free up delivery agent
        if order.delivery_agent_id:
            agent = self.delivery_agents[order.delivery_agent_id]
            if order_id in agent.current_orders:
                agent.current_orders.remove(order_id)
            
            if not agent.current_orders:
                agent.status = "available"
        
        # Calculate delivery performance
        delivery_time = (order.actual_delivery_time - order.estimated_delivery_time).total_seconds() / 60
        on_time = delivery_time <= 15  # Within 15 minutes is considered on time
        
        print(f"✅ Order {order_id} delivered {'on time' if on_time else 'late'} "
              f"({delivery_time:+.0f} minutes from estimate)")
        
        # Send delivery confirmation with rating request
        self._send_delivery_confirmation(order)
    
    def _send_delivery_confirmation(self, order: Order):
        """Send delivery confirmation and request rating"""
        customer = self.customers[order.customer_id]
        
        message = f"✅ Delivery completed!\n" \
                 f"📦 Order #{order.order_id[-8:]}\n" \
                 f"🕒 Delivered at: {order.actual_delivery_time.strftime('%I:%M %p')}\n" \
                 f"💰 Total: ${order.total_amount:.2f}\n" \
                 f"⭐ Rate your experience: http://rate.s2d.com/{order.order_id}\n" \
                 f"📧 Receipt sent to {customer.email}"
        
        # Send notifications
        for notification_type in customer.preferred_notifications:
            if notification_type == NotificationType.SMS:
                self.notifications.send_sms(customer.phone, message)
            elif notification_type == NotificationType.WHATSAPP:
                self.notifications.send_whatsapp(customer.phone, message)
    
    def simulate_delivery_progress(self, order_id: str):
        """Simulate the delivery progress for an order"""
        order = self.active_orders.get(order_id)
        if not order or not order.delivery_agent_id:
            return
        
        agent = self.delivery_agents[order.delivery_agent_id]
        
        # Simulate movement towards delivery location
        current_location = self.geolocation.get_agent_location(agent.agent_id)
        if not current_location:
            return
        
        # Move agent closer to destination
        lat_diff = order.delivery_lat - current_location["lat"]
        lng_diff = order.delivery_lng - current_location["lng"]
        
        # Move 10% closer each time
        new_lat = current_location["lat"] + (lat_diff * 0.1)
        new_lng = current_location["lng"] + (lng_diff * 0.1)
        
        self.geolocation.update_agent_location(agent.agent_id, new_lat, new_lng)
        
        # Calculate distance remaining
        distance_remaining = self.geolocation.calculate_distance(
            new_lat, new_lng, order.delivery_lat, order.delivery_lng
        )
        
        # Update tracking
        if distance_remaining < 0.1:  # Within 100 meters
            if order.status != OrderStatus.DELIVERED:
                self.update_order_status(order_id, OrderStatus.DELIVERED, "Package delivered!")
        elif distance_remaining < 0.5:  # Within 500 meters
            self._add_tracking_update(order_id, "Driver is nearby (within 500m)", {
                "distance_remaining_km": round(distance_remaining, 2)
            })
        
        return distance_remaining
    
    def start_tracking_simulation(self):
        """Start the continuous tracking simulation"""
        self.is_running = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        print("🔄 Started order tracking simulation")
    
    def stop_tracking_simulation(self):
        """Stop the tracking simulation"""
        self.is_running = False
        if self.tracking_thread:
            self.tracking_thread.join()
        print("⏹️ Stopped order tracking simulation")
    
    def _tracking_loop(self):
        """Main tracking simulation loop"""
        while self.is_running:
            try:
                # Update all active deliveries
                active_deliveries = [
                    order for order in self.active_orders.values()
                    if order.status in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.PREPARING]
                ]
                
                for order in active_deliveries:
                    if order.status == OrderStatus.PREPARING:
                        # Random chance to start delivery
                        if random.random() < 0.1:  # 10% chance per cycle
                            self.update_order_status(
                                order.order_id, 
                                OrderStatus.OUT_FOR_DELIVERY, 
                                "Driver has picked up your order and is on the way!"
                            )
                    
                    elif order.status == OrderStatus.OUT_FOR_DELIVERY:
                        # Simulate delivery progress
                        self.simulate_delivery_progress(order.order_id)
                
                time.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                print(f"❌ Error in tracking loop: {e}")
                time.sleep(5)
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get current order status and tracking information"""
        order = self.active_orders.get(order_id)
        if not order:
            return None
        
        agent_location = None
        eta_minutes = None
        
        if order.delivery_agent_id:
            agent_location = self.geolocation.get_agent_location(order.delivery_agent_id)
            if agent_location and order.status == OrderStatus.OUT_FOR_DELIVERY:
                eta_minutes = self.geolocation.calculate_eta(
                    order.delivery_agent_id, order.delivery_lat, order.delivery_lng
                )
        
        return {
            "order_id": order.order_id,
            "status": order.status.value,
            "customer_id": order.customer_id,
            "products": order.products,
            "total_amount": order.total_amount,
            "delivery_address": order.delivery_address,
            "estimated_delivery_time": order.estimated_delivery_time.isoformat(),
            "actual_delivery_time": order.actual_delivery_time.isoformat() if order.actual_delivery_time else None,
            "delivery_agent_id": order.delivery_agent_id,
            "agent_location": agent_location,
            "eta_minutes": eta_minutes,
            "tracking_updates": order.tracking_updates
        }

# Example usage and testing
def demo_customer_tracking():
    """Demonstrate the customer tracking system"""
    print("🚀 Starting Customer Tracking Demo")
    
    # Initialize system
    tracking_system = OrderTrackingSystem()
    tracking_system.start_tracking_simulation()
    
    try:
        # Create sample orders
        sample_products = [
            {"product_id": "MILK_001", "name": "Organic Milk 1L", "price": 4.99, "quantity": 2},
            {"product_id": "BREAD_001", "name": "Whole Wheat Bread", "price": 2.49, "quantity": 1}
        ]
        
        # Create orders for different customers
        order1 = tracking_system.create_order("CUST_001", sample_products)
        time.sleep(2)
        
        order2 = tracking_system.create_order("CUST_002", [
            {"product_id": "APPLE_001", "name": "Red Apples", "price": 3.99, "quantity": 3}
        ])
        
        print(f"📦 Created orders: {order1}, {order2}")
        
        # Simulate order progression
        time.sleep(5)
        tracking_system.update_order_status(order1, OrderStatus.PREPARING, "Order is being prepared in the kitchen")
        
        time.sleep(10)
        
        # Let the simulation run
        print("🔄 Simulation running... Orders will progress automatically")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(30)
            
            # Print status updates
            for order_id in [order1, order2]:
                status = tracking_system.get_order_status(order_id)
                if status:
                    print(f"📊 {order_id}: {status['status']} - ETA: {status.get('eta_minutes', 'N/A')} min")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
        tracking_system.stop_tracking_simulation()
        print("Demo stopped")

if __name__ == "__main__":
    demo_customer_tracking()