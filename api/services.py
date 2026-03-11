# api/services.py
from datetime import datetime, timezone, timedelta
from config.firebase import db

class IoTService:

    # Fallback thresholds (used ONLY if no crop is assigned to a node)
    DEFAULT_THRESHOLDS = {
        "moisture_min": 30.0,
        "moisture_max": 80.0,
        "ph_min": 5.5,
        "ph_max": 7.5,
        "temp_min": 15.0,
        "temp_max": 35.0,
    }

    NODE_TIMEOUT_MINUTES = 10

    @classmethod
    def process_reading(cls, data):
        """Processes incoming hardware data, saves it, and triggers alerts."""
        node_id = data.get("node_id")
        if not node_id:
            raise ValueError("node_id is required")

        # 1. Prepare payload with a UTC timestamp
        payload = data.copy()
        payload["timestamp"] = datetime.now(timezone.utc)

        # 2. Save to historical readings collection
        db.collection("readings").document(node_id).collection("history").add(payload)

        # 3. Update the node's current status and latest readings
        node_ref = db.collection("nodes").document(node_id)
        node_doc = node_ref.get()
        
        # Keep the existing name if it exists, otherwise use a default
        node_name = data.get("node_name", f"Node {node_id}")
        if node_doc.exists and "node_name" in node_doc.to_dict() and not data.get("node_name"):
            node_name = node_doc.to_dict()["node_name"]

        node_data = {
            "node_id": node_id,
            "node_name": node_name,
            "status": "online",
            "last_seen": payload["timestamp"],
            "lastReading": payload
        }
        # Use merge=True so we don't accidentally delete crop_type
        node_ref.set(node_data, merge=True)

        # 👇 ADD THIS LINE TO FIX THE STUCK ALERT 👇
        cls.resolve_alert(node_id, "disconnected")

        # 4. Fetch thresholds and Check for Alerts!
        thresholds = cls.get_thresholds_for_node(node_id)
        cls.check_sensor_alerts(node_id, data, thresholds)

        return payload

    @staticmethod
    def get_thresholds_for_node(node_id, sensor_data=None):
        """Fetches crop-specific thresholds from Firebase."""
        try:
            node_doc = db.collection("nodes").document(node_id).get()
            crop_type = "default"

            if node_doc.exists:
                crop_type = node_doc.to_dict().get("crop_type", "default")

            doc_id = crop_type.lower().replace(" ", "_") if crop_type != "default" else "default"
            
            # 1. First, try to find it by the exact Document ID
            config_doc = db.collection("crop_config").document(doc_id).get()

            if config_doc.exists:
                config_data = config_doc.to_dict()
                return config_data.get("thresholds", config_data)
            
            # 2. FALLBACK: Search by the 'crop_id' field!
            query = db.collection("crop_config").where("crop_id", "==", doc_id).get()
            if query:
                # Grab the first matching document from the search
                config_data = query[0].to_dict()
                return config_data.get("thresholds", config_data)
                
            print(f"⚠️ DEBUG: Could not find crop config for '{doc_id}'. Falling back to defaults.")
            return IoTService.DEFAULT_THRESHOLDS
            
        except Exception as e:
            print(f"Error fetching thresholds: {e}")
            return IoTService.DEFAULT_THRESHOLDS

    @classmethod
    def check_sensor_alerts(cls, node_id, data, thresholds, node_name=None):
        """Evaluates live sensor data against the assigned thresholds."""
        # Use node_name for display, but keep node_id for the database logic
        display_name = node_name if node_name else node_id
        
        # --- MOISTURE ALERTS ---
        if "moisture" in data:
            val = float(data["moisture"])
            min_val = float(thresholds.get("moisture_min", cls.DEFAULT_THRESHOLDS["moisture_min"]))
            max_val = float(thresholds.get("moisture_max", cls.DEFAULT_THRESHOLDS["moisture_max"]))
            
            if val < min_val:
                cls.trigger_alert(node_id, "moisture", f"{display_name}: Soil is too dry ({val}%). Below {min_val}%.", "warning", "moisture", val)
            elif val > max_val:
                cls.trigger_alert(node_id, "moisture", f"{display_name}: Soil is too wet ({val}%). Above {max_val}%.", "warning", "moisture", val)
            else:
                cls.resolve_alert(node_id, "moisture")

        # --- TEMPERATURE ALERTS ---
        if "temperature" in data:
            val = float(data["temperature"])
            min_val = float(thresholds.get("temp_min", cls.DEFAULT_THRESHOLDS["temp_min"]))
            max_val = float(thresholds.get("temp_max", cls.DEFAULT_THRESHOLDS["temp_max"]))
            
            if val < min_val:
                cls.trigger_alert(node_id, "temperature", f"{display_name}: Soil too cold ({val}°C). Below {min_val}°C.", "warning", "temperature", val)
            elif val > max_val:
                cls.trigger_alert(node_id, "temperature", f"{display_name}: Soil too hot ({val}°C). Above {max_val}°C.", "critical", "temperature", val)
            else:
                cls.resolve_alert(node_id, "temperature")

        # --- PH ALERTS ---
        if "ph" in data or "pH" in data:
            val = float(data.get("ph", data.get("pH")))
            min_val = float(thresholds.get("ph_min", cls.DEFAULT_THRESHOLDS["ph_min"]))
            max_val = float(thresholds.get("ph_max", cls.DEFAULT_THRESHOLDS["ph_max"]))
            
            if val < min_val:
                cls.trigger_alert(node_id, "ph", f"{display_name}: Soil is too acidic (pH {val}).", "warning", "ph", val)
            elif val > max_val:
                cls.trigger_alert(node_id, "ph", f"{display_name}: Soil is too alkaline (pH {val}).", "warning", "ph", val)
            else:
                cls.resolve_alert(node_id, "ph")

    @classmethod
    def recalculate_alerts_for_node(cls, node_id):
        """Re-evaluates the latest sensor readings against current thresholds."""
        print(f"--- DEBUG: Recalculating alerts for node: {node_id} ---")
        
        node_doc = db.collection("nodes").document(node_id).get()
        
        if not node_doc.exists:
            query = db.collection("nodes").where("node_id", "==", node_id).get()
            if not query:
                print(f"DEBUG: ❌ Could not find node '{node_id}' in database.")
                return
            node_doc = query[0]

        node_data = node_doc.to_dict()
        
        # --- NEW: Get the human-readable name ---
        node_name = node_data.get("node_name", node_id) 
        
        # Use 'lastReading' as per your Firebase structure
        latest_readings = node_data.get("lastReading")

        if latest_readings:
            print(f"DEBUG: ✅ Found latest readings for {node_name}: {latest_readings}")
            thresholds = cls.get_thresholds_for_node(node_id)
            
            # --- Pass node_name to the check function ---
            cls.check_sensor_alerts(node_id, latest_readings, thresholds, node_name)
            print(f"DEBUG: ✅ Finished checking sensor alerts for {node_name}!")
        else:
            print(f"DEBUG: ⚠️ No 'lastReading' found for {node_name} yet.")
    
    @classmethod
    def trigger_alert(cls, node_id, alert_type, message, severity, parameter, current_value):
        """Creates a new alert if one doesn't already exist to prevent database spam."""
        alerts_ref = db.collection("alerts")
        
        existing = alerts_ref.where("node_id", "==", node_id) \
                             .where("alert_type", "==", alert_type) \
                             .where("status", "==", "active").get()
                             
        if len(existing) == 0:
            alerts_ref.add({
                "node_id": node_id,
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "parameter": parameter,
                "current_value": current_value,
                "status": "active",
                "is_read": False,
                "created_at": datetime.now(timezone.utc)
            })

    @classmethod
    def resolve_alert(cls, node_id, alert_type):
        """Marks an alert as resolved when conditions return to normal."""
        alerts_ref = db.collection("alerts")
        
        existing = alerts_ref.where("node_id", "==", node_id) \
                             .where("alert_type", "==", alert_type) \
                             .where("status", "==", "active").get()
                             
        for alert in existing:
            alert.reference.update({
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc)
            })

    @classmethod
    def check_node_connectivity(cls):
        """Checks if any nodes have stopped sending data and marks them offline."""
        nodes_ref = db.collection("nodes").stream()
        timeout = timedelta(minutes=cls.NODE_TIMEOUT_MINUTES)

        for node_doc in nodes_ref:
            node = node_doc.to_dict()
            last_seen = node.get("last_seen")

            if last_seen:
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                time_diff = now_utc - last_seen
                safe_node_id = node.get("node_id") or node_doc.id

                if time_diff > timeout and node.get("status") != "offline":
                    node_doc.reference.update({"status": "offline"})
                elif time_diff <= timeout and node.get("status") == "offline":
                    node_doc.reference.update({"status": "online"})