# populate_soil_node_data_realtime.py
import random
import time
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000/api/v1/ingest/"
NODES = ["soil_node_01", "soil_node_02"]  # Add more nodes as needed

# Interval between readings (in seconds)
READING_INTERVAL = 5  # Send data every 5 seconds

print(f"🌱 REAL-TIME SOIL NODE SIMULATOR")
print(f"=" * 50)
print(f"Monitoring {len(NODES)} soil nodes")
print(f"Reading interval: {READING_INTERVAL} seconds")
print(f"Press Ctrl+C to stop\n")

# Initialize base values for gradual changes
node_states = {}
for node in NODES:
    node_states[node] = {
        "battery": random.uniform(80, 95),
        "moisture": random.uniform(40, 60),
        "soil_temp": random.uniform(26, 30),
        "air_temp": random.uniform(28, 32),
        "humidity": random.uniform(55, 70),
        "ph": random.uniform(6.2, 7.0),
        "nitrogen": random.uniform(110, 140),
        "phosphorus": random.uniform(35, 45),
        "potassium": random.uniform(160, 190),
    }

reading_count = 0

try:
    while True:
        reading_count += 1
        current_time = datetime.now() #change to ph timezone
        
        print(f"\n📊 Reading #{reading_count} - {current_time.strftime('%H:%M:%S')}")
        print("-" * 50)
        
        for node_id in NODES:
            state = node_states[node_id]
            
            # Simulate gradual changes (more realistic than random)
            # Battery slowly drains
            state["battery"] -= random.uniform(0.01, 0.05)
            state["battery"] = max(10, state["battery"])  # Don't go below 10%
            
            # Moisture slowly changes
            state["moisture"] += random.uniform(-2, 2)
            state["moisture"] = max(20, min(80, state["moisture"]))  # Keep in range 20-80%
            
            # Temperature fluctuates slightly
            state["soil_temp"] += random.uniform(-0.5, 0.5)
            state["soil_temp"] = max(20, min(35, state["soil_temp"]))
            
            state["air_temp"] += random.uniform(-0.5, 0.5)
            state["air_temp"] = max(22, min(38, state["air_temp"]))
            
            # Humidity changes
            state["humidity"] += random.uniform(-1, 1)
            state["humidity"] = max(30, min(90, state["humidity"]))
            
            # pH is relatively stable
            state["ph"] += random.uniform(-0.05, 0.05)
            state["ph"] = max(5.0, min(8.0, state["ph"]))
            
            # NPK values change slowly
            state["nitrogen"] += random.uniform(-2, 2)
            state["phosphorus"] += random.uniform(-1, 1)
            state["potassium"] += random.uniform(-2, 2)
            
            # Build data payload
            data = {
                "node_id": node_id,
                "node_name": f"Soil Node {node_id.split('_')[-1]}",
                
                # Battery percentage
                "battery_percentage": round(state["battery"], 1),
                
                # Soil sensor data (NO CONDUCTIVITY)
                "moisture": round(state["moisture"], 1),
                "temperature": round(state["soil_temp"], 1),
                "ph": round(state["ph"], 1),
                "nitrogen": round(state["nitrogen"], 0),
                "phosphorus": round(state["phosphorus"], 0),
                "potassium": round(state["potassium"], 0),
                
                # Environmental data
                "air_temperature": round(state["air_temp"], 1),
                "humidity": round(state["humidity"], 1),
            }
            
            try:
                response = requests.post(API_URL, json=data, timeout=3)
                if response.status_code == 201:
                    # Format output with icons
                    battery_icon = "🔋" if state["battery"] > 50 else "🪫"
                    moisture_icon = "💧" if state["moisture"] < 40 else "💦"
                    
                    print(f"✅ {node_id}: "
                          f"{battery_icon} {data['battery_percentage']}% | "
                          f"{moisture_icon} {data['moisture']}% | "
                          f"🌡️  {data['temperature']}°C | "
                          f"pH {data['ph']}")
                else:
                    print(f"❌ {node_id}: Error - {response.status_code}")
                    print(f"   Response: {response.text[:100]}")
            except requests.exceptions.Timeout:
                print(f"⏱️  {node_id}: Request timeout")
            except requests.exceptions.ConnectionError:
                print(f"🔌 {node_id}: Connection failed - Is Django running?")
                print(f"   Make sure server is running at {API_URL}")
                break
            except Exception as e:
                print(f"⚠️  {node_id}: Error - {str(e)[:50]}")
        
        # Wait before next reading
        print(f"\n⏳ Next reading in {READING_INTERVAL} seconds...")
        time.sleep(READING_INTERVAL)

except KeyboardInterrupt:
    print(f"\n\n🛑 Simulation stopped by user")
    print(f"📈 Total readings sent: {reading_count}")
    print(f"👋 Goodbye!")