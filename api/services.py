# api/services.py
from datetime import datetime, timedelta
from config.firebase import db


class IoTService:

    # Fallback thresholds (used ONLY if no document has been uploaded)
    DEFAULT_THRESHOLDS = {
        "moisture_min": 30.0,
        "moisture_max": 80.0,
        "ph_min": 5.5,
        "ph_max": 7.5,
        "temp_min": 15.0,
        "temp_max": 35.0,
        "battery_min": 20.0,
    }

    NODE_TIMEOUT_MINUTES = 10

    @staticmethod
    def get_thresholds_for_node(node_id):
        """
        Fetch thresholds from Firebase (extracted from uploaded documents).
        Falls back to DEFAULT_THRESHOLDS only if no document uploaded yet.
        """
        try:
            # Get the node's assigned crop type
            node_doc = db.collection("nodes").document(node_id).get()
            crop_type = "default"

            if node_doc.exists:
                crop_type = node_doc.to_dict().get("crop_type", "default")

            # Look up thresholds in Firebase crop_config
            doc_id = crop_type.lower().replace(" ", "_") if crop_type != "default" else "default"
            config_doc = db.collection("crop_config").document(doc_id).get()

            if config_doc.exists:
                config = config_doc.to_dict()
                # Only use values that are not None
                thresholds = {}
                for key, fallback in IoTService.DEFAULT_THRESHOLDS.items():
                    value = config.get(key)
                    thresholds[key] = value if value is not None else fallback
                thresholds["battery_min"] = IoTService.DEFAULT_THRESHOLDS["battery_min"]
                print(f"✓ Using document-based thresholds for {node_id} (crop: {crop_type})")
                return thresholds

        except Exception as e:
            print(f"Error fetching thresholds: {e}")

        # Fallback to hardcoded defaults
        print(f"⚠ Using default thresholds for {node_id} (no document uploaded yet)")
        return IoTService.DEFAULT_THRESHOLDS.copy()

    @staticmethod
    def process_reading(data):
        """
        Process sensor data from individual soil nodes.
        Uses document-extracted thresholds for alert evaluation.
        """
        node_id = data.get("node_id")
        if not node_id:
            raise ValueError("node_id is required")

        payload = {
            "node_id": node_id,
            "battery_percentage": float(data.get("battery_percentage", 0)),
            "moisture": float(data.get("moisture", 0)),
            "temperature": float(data.get("temperature", 0)),
            "ph": float(data.get("ph", 0)),
            "nitrogen": float(data.get("nitrogen", 0)),
            "phosphorus": float(data.get("phosphorus", 0)),
            "potassium": float(data.get("potassium", 0)),
            "air_temperature": float(data.get("air_temperature", 0)),
            "humidity": float(data.get("humidity", 0)),
            "timestamp": datetime.now(),
            "status": "online"
        }

        # Save to historical readings
        db.collection("readings").document(node_id).collection("history").add(payload)

        # Update node's current status
        db.collection("nodes").document(node_id).set({
            "node_id": node_id,
            "node_name": data.get("node_name", f"Soil Node {node_id.split('_')[-1]}"),
            "crop_type": data.get("crop_type", "default"),
            "last_seen": datetime.now(),
            "status": "online",
            "latest_readings": payload
        }, merge=True)

        # Fetch document-based thresholds and evaluate alerts
        thresholds = IoTService.get_thresholds_for_node(node_id)
        IoTService.evaluate_alerts(node_id, payload, thresholds)

        return payload

    @staticmethod
    def evaluate_alerts(node_id, data, thresholds):
        """Evaluate sensor data against document-based thresholds"""

        current_violations = {}

        # Battery
        if data["battery_percentage"] < thresholds.get("battery_min", 20.0):
            current_violations["battery_low"] = {
                "message": f"{node_id}: Low Battery ({data['battery_percentage']}%)",
                "severity": "high",
                "parameter": "battery",
                "value": data["battery_percentage"]
            }

        # Moisture
        if data["moisture"] < thresholds["moisture_min"]:
            current_violations["moisture_low"] = {
                "message": f"{node_id}: Low Moisture ({data['moisture']}%) - Below {thresholds['moisture_min']}%",
                "severity": "high",
                "parameter": "moisture",
                "value": data["moisture"]
            }
        elif data["moisture"] > thresholds["moisture_max"]:
            current_violations["moisture_high"] = {
                "message": f"{node_id}: Excess Moisture ({data['moisture']}%) - Above {thresholds['moisture_max']}%",
                "severity": "medium",
                "parameter": "moisture",
                "value": data["moisture"]
            }

        # pH
        if data["ph"] < thresholds["ph_min"]:
            current_violations["ph_low"] = {
                "message": f"{node_id}: Soil Too Acidic (pH {data['ph']}) - Below {thresholds['ph_min']}",
                "severity": "medium",
                "parameter": "ph",
                "value": data["ph"]
            }
        elif data["ph"] > thresholds["ph_max"]:
            current_violations["ph_high"] = {
                "message": f"{node_id}: Soil Too Alkaline (pH {data['ph']}) - Above {thresholds['ph_max']}",
                "severity": "medium",
                "parameter": "ph",
                "value": data["ph"]
            }

        # Temperature
        if data["temperature"] > thresholds["temp_max"]:
            current_violations["temp_high"] = {
                "message": f"{node_id}: Heat Stress ({data['temperature']}°C) - Above {thresholds['temp_max']}°C",
                "severity": "high",
                "parameter": "temperature",
                "value": data["temperature"]
            }
        elif data["temperature"] < thresholds["temp_min"]:
            current_violations["temp_low"] = {
                "message": f"{node_id}: Low Temperature ({data['temperature']}°C) - Below {thresholds['temp_min']}°C",
                "severity": "medium",
                "parameter": "temperature",
                "value": data["temperature"]
            }

        # Fetch active alerts and resolve/create
        active_alerts = (
            db.collection("alerts")
            .where("node_id", "==", node_id)
            .where("status", "==", "active")
            .stream()
        )
        active_alert_map = {
            alert.to_dict()["alert_type"]: alert
            for alert in active_alerts
        }

        # Resolve cleared alerts
        for alert_type, alert_doc in active_alert_map.items():
            if alert_type not in current_violations:
                alert_doc.reference.update({
                    "status": "resolved",
                    "resolved_at": datetime.now()
                })

        # Create new alerts
        for alert_type, alert_data in current_violations.items():
            if alert_type not in active_alert_map:
                db.collection("alerts").add({
                    "node_id": node_id,
                    "alert_type": alert_type,
                    "message": alert_data["message"],
                    "severity": alert_data["severity"],
                    "parameter": alert_data["parameter"],
                    "current_value": alert_data["value"],
                    "threshold_used": thresholds,
                    "status": "active",
                    "is_read": False,
                    "created_at": datetime.now()
                })

    @staticmethod
    def check_node_connectivity():
        """Check all nodes for disconnection"""
        nodes_ref = db.collection("nodes").stream()
        timeout = timedelta(minutes=IoTService.NODE_TIMEOUT_MINUTES)

        for node_doc in nodes_ref:
            node = node_doc.to_dict()
            node_id = node.get("node_id")
            last_seen = node.get("last_seen")

            if last_seen:
                time_diff = datetime.now() - last_seen

                if time_diff > timeout and node.get("status") != "offline":
                    node_doc.reference.update({"status": "offline"})
                    db.collection("alerts").add({
                        "node_id": node_id,
                        "alert_type": "disconnected",
                        "message": f"{node_id}: Node Disconnected/Offline",
                        "severity": "critical",
                        "parameter": "connectivity",
                        "current_value": "offline",
                        "status": "active",
                        "is_read": False,
                        "created_at": datetime.now()
                    })
                elif time_diff <= timeout and node.get("status") == "offline":
                    node_doc.reference.update({"status": "online"})
                    alerts = (
                        db.collection("alerts")
                        .where("node_id", "==", node_id)
                        .where("alert_type", "==", "disconnected")
                        .where("status", "==", "active")
                        .stream()
                    )
                    for alert in alerts:
                        alert.reference.update({
                            "status": "resolved",
                            "resolved_at": datetime.now()
                        })