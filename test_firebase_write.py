import requests
import json

API_URL = "http://127.0.0.1:8000/api/v1/ingest/"

# Test data for Node 1
test_data = {
    "gateway_id": "arduino_gateway_01",
    "node_id": "node_1",
    "node_name": "Node 1",
    "moisture": 45.5,
    "temperature": 28.2,
    "ph": 6.5,
    "nitrogen": 120,
    "phosphorus": 40,
    "potassium": 180,
    "humidity": 60,
    "conductivity": 450,
    "total_nodes": 2
}

print("=" * 60)
print("TESTING FIREBASE DATA INGESTION")
print("=" * 60)
print(f"\nAPI URL: {API_URL}")
print(f"\nSending data:")
print(json.dumps(test_data, indent=2))
print("\n" + "-" * 60)

try:
    response = requests.post(API_URL, json=test_data)
    
    print(f"\n✓ Response Status: {response.status_code}")
    print(f"\n✓ Response Body:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 201:
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Data sent to Django API")
        print("=" * 60)
        print("\nNow check:")
        print("1. Django console for any errors")
        print("2. Firebase Console → Firestore Database")
        print("3. Look for these collections:")
        print("   - gateways/arduino_gateway_01")
        print("   - nodes/arduino_gateway_01_node_1")
        print("   - readings/arduino_gateway_01/node_1/")
        print("\nIf you don't see data in Firebase:")
        print("• Check Firestore Rules (should allow write: if true)")
        print("• Check serviceAccountKey.json is correct")
        print("• Look at Django terminal for errors")
    else:
        print("\n" + "=" * 60)
        print(f"⚠️ WARNING: Unexpected status code {response.status_code}")
        print("=" * 60)
        
except requests.exceptions.ConnectionError:
    print("\n" + "=" * 60)
    print("❌ ERROR: Cannot connect to Django server")
    print("=" * 60)
    print("\nMake sure Django is running:")
    print("  python manage.py runserver")
    
except Exception as e:
    print("\n" + "=" * 60)
    print(f"❌ ERROR: {str(e)}")
    print("=" * 60)