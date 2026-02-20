# api/knowledge_library_service.py

from datetime import datetime
from config.firebase import db


class KnowledgeLibraryService:
    """
    Manages the crop profile library in Firebase.
    
    Firebase Structure:
    ├── crop_profiles/              ← Permanent crop library (never overwritten)
    │   ├── tomato/                 ← { name, thresholds, documents, created_at }
    │   ├── rice/
    │   └── corn/
    │
    └── settings/
        └── global/                 ← { active_crop: "tomato" }
    """

    # ─────────────────────── CROP PROFILES ───────────────────────

    @staticmethod
    def save_crop_profile(crop_type, thresholds, document_name, description=""):
        """
        Save or update a crop profile in the library.
        NEVER overwrites — always merges so library grows over time.
        """
        crop_id = crop_type.lower().strip().replace(" ", "_")

        # Get existing profile (if any)
        existing_doc = db.collection("crop_profiles").document(crop_id).get()
        existing = existing_doc.to_dict() if existing_doc.exists else {}

        # Build updated document list
        documents = existing.get("documents", [])
        if document_name not in documents:
            documents.append(document_name)

        profile = {
            "crop_id": crop_id,
            "crop_name": crop_type.title(),
            "description": description or existing.get("description", ""),
            "thresholds": thresholds or existing.get("thresholds", {}),
            "documents": documents,
            "document_count": len(documents),
            "created_at": existing.get("created_at", datetime.now()),
            "updated_at": datetime.now(),
            "is_active": False  # Not active until user selects it
        }

        db.collection("crop_profiles").document(crop_id).set(profile, merge=True)
        print(f"✓ Saved crop profile: {crop_id}")
        return profile

    @staticmethod
    def get_all_crop_profiles():
        """Get all crops in the library for dropdown"""
        profiles = []
        try:
            docs = db.collection("crop_profiles").stream()
            for doc in docs:
                data = doc.to_dict()
                profiles.append({
                    "crop_id": doc.id,
                    "crop_name": data.get("crop_name", doc.id.title()),
                    "description": data.get("description", ""),
                    "document_count": data.get("document_count", 0),
                    "documents": data.get("documents", []),
                    "thresholds": data.get("thresholds", {}),
                    "is_active": data.get("is_active", False),
                    "updated_at": data.get("updated_at")
                })
        except Exception as e:
            print(f"Error fetching crop profiles: {e}")
        return sorted(profiles, key=lambda x: x["crop_name"])

    @staticmethod
    def get_crop_profile(crop_type):
        """Get a single crop profile"""
        crop_id = crop_type.lower().strip().replace(" ", "_")
        doc = db.collection("crop_profiles").document(crop_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    @staticmethod
    def delete_crop_profile(crop_type):
        """Delete a crop profile from library"""
        crop_id = crop_type.lower().strip().replace(" ", "_")
        db.collection("crop_profiles").document(crop_id).delete()
        # Also delete from crop_config (thresholds)
        db.collection("crop_config").document(crop_id).delete()
        print(f"✓ Deleted crop profile: {crop_id}")

    # ─────────────────────── ACTIVE CROP SELECTION ───────────────────────

    @staticmethod
    def set_active_crop_for_node(node_id, crop_type):
        """
        Set the active crop for a specific node.
        This is what the dropdown triggers.
        """
        crop_id = crop_type.lower().strip().replace(" ", "_")

        # Update the node's active crop
        db.collection("nodes").document(node_id).update({
            "crop_type": crop_id,
            "crop_updated_at": datetime.now()
        })

        # Fetch the profile thresholds
        profile = KnowledgeLibraryService.get_crop_profile(crop_id)
        thresholds = profile.get("thresholds", {}) if profile else {}

        # Save thresholds to crop_config for fast access by alert system
        if thresholds:
            db.collection("crop_config").document(crop_id).set(
                {**thresholds, "source": "crop_profiles", "crop_type": crop_id},
                merge=True
            )

        print(f"✓ Node {node_id} → active crop: {crop_id}")
        return {"node_id": node_id, "active_crop": crop_id, "thresholds": thresholds}

    @staticmethod
    def get_active_crop_for_node(node_id):
        """Get the currently active crop for a node"""
        node_doc = db.collection("nodes").document(node_id).get()
        if node_doc.exists:
            return node_doc.to_dict().get("crop_type", "default")
        return "default"

    @staticmethod
    def get_active_thresholds_for_node(node_id):
        """
        THE KEY FUNCTION — used by both IoTService and AIChatService.
        Gets thresholds for the node's currently selected crop.
        
        Priority:
        1. crop_profiles/{active_crop}/thresholds
        2. crop_config/{active_crop}
        3. Hardcoded fallback
        """
        fallback = {
            "moisture_min": 30.0, "moisture_max": 80.0,
            "ph_min": 5.5, "ph_max": 7.5,
            "temp_min": 15.0, "temp_max": 35.0,
        }

        try:
            crop_type = KnowledgeLibraryService.get_active_crop_for_node(node_id)

            if crop_type and crop_type != "default":
                profile = KnowledgeLibraryService.get_crop_profile(crop_type)
                if profile and profile.get("thresholds"):
                    t = profile["thresholds"]
                    # Merge with fallback for any missing values
                    return {key: t.get(key) or fallback[key] for key in fallback}, crop_type

            # Try crop_config as secondary
            crop_config = db.collection("crop_config").document(
                crop_type if crop_type else "default"
            ).get()
            if crop_config.exists:
                t = crop_config.to_dict()
                return {key: t.get(key) or fallback[key] for key in fallback}, crop_type

        except Exception as e:
            print(f"Error getting thresholds: {e}")

        return fallback, "default"