from datetime import datetime
from config.firebase import db

def fix_legacy_alerts():
    alerts = db.collection("alerts").stream()

    fixed = 0
    skipped = 0

    for alert in alerts:
        data = alert.to_dict()

        if "status" not in data:
            try:
                alert.reference.set(
                    {
                        "status": "resolved",
                        "resolved_at": datetime.now(),
                    },
                    merge=True  # 🔥 KEY FIX
                )
                fixed += 1
            except Exception as e:
                print(f"❌ Failed on alert {alert.id}: {e}")
        else:
            skipped += 1

    print(f"✅ Fixed {fixed} legacy alerts")
    print(f"⏭️ Skipped {skipped} already-correct alerts")

if __name__ == "__main__":
    fix_legacy_alerts()
