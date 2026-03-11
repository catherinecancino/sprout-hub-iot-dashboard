import time
from datetime import datetime, timezone

from pymodbus.client import ModbusSerialClient
import adafruit_dht
from adafruit_blinka.microcontroller.bcm283x import pin

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# DEVICE CONFIG (PI #2)
# -------------------------
NODE_ID = "rpi_2"
NODE_NAME = "Node B"

PROJECT_ID = "agritech-iot-847f1"
SERVICE_KEY = "serviceAccountKey.json"

# -------------------------
# RS485 SETTINGS
# -------------------------
PORT = "/dev/ttyUSB0"
BAUD = 4800
SLAVE_ID = 1

SOIL_SAMPLES = 10
SOIL_DELAY = 1

# -------------------------
# DHT SETTINGS
# -------------------------
DHT_SENSOR = adafruit_dht.DHT11(pin.D17, use_pulseio=False)
time.sleep(2)

# -------------------------
# Time sanity check
# -------------------------
now_utc = datetime.now(timezone.utc)
if now_utc.year < 2020:
    print("⚠️ Your Pi clock looks wrong:", now_utc.isoformat())
    print("Firestore will FAIL until the system time is corrected.\n")

# -------------------------
# Firebase Init
# -------------------------
cred = credentials.Certificate(SERVICE_KEY)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
db = firestore.client()

# -------------------------
# Last-known-good cache
# -------------------------
last_air_temp = None
last_humidity = None

last_soil = {
    "moisture": None,
    "temperature": None,
    "ec": None,
    "pH": None,
    "nitrogen": None,
    "phosphorus": None,
    "potassium": None,
}

# -------------------------
# Helpers
# -------------------------
def int16_signed(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x

def safe_avg(values):
    return sum(values) / len(values) if values else None

def read_dht():
    try:
        t = DHT_SENSOR.temperature
        h = DHT_SENSOR.humidity
        if t is None or h is None:
            return None, None
        return float(t), float(h)
    except Exception:
        return None, None

def modbus_read(client):
    for _ in range(3):
        r = client.read_holding_registers(address=0x0000, count=9, slave=SLAVE_ID)
        if not r.isError():
            return r
        time.sleep(0.2)
    return None

def print_terminal(data):
    print("\n==============================")
    print(f"Node: {NODE_NAME}")
    print(f"Time (UTC): {data['timestamp'].isoformat()}")

    print("\nSoil (RS485):")
    print(f"  Moisture:   {data['moisture']}")
    print(f"  Temp:       {data['temperature']}")
    print(f"  EC:         {data['ec']}")
    print(f"  pH:         {data['pH']}")
    print(f"  N:          {data['nitrogen']}")
    print(f"  P:          {data['phosphorus']}")
    print(f"  K:          {data['potassium']}")

    print("\nAir (DHT):")
    print(f"  Air Temp:   {data['air_temperature']}")
    print(f"  Humidity:   {data['humidity']}")
    print("==============================")

# -------------------------
# Modbus Client
# -------------------------
client = ModbusSerialClient(
    port=PORT,
    baudrate=BAUD,
    parity="N",
    stopbits=1,
    bytesize=8,
    timeout=1.0
)

if not client.connect():
    raise SystemExit("Modbus connection failed.")

# -------------------------
# MAIN LOOP
# -------------------------
try:
    while True:

        moist, temp_s, ec_l, ph_l = [], [], [], []
        n_l, p_l, k_l = [], [], []

        for _ in range(SOIL_SAMPLES):

            resp = modbus_read(client)

            if resp is None:
                time.sleep(SOIL_DELAY)
                continue

            r = resp.registers

            moist.append(r[0] / 10.0)
            temp_s.append(int16_signed(r[1]) / 10.0)
            ec_l.append(r[2])
            ph_l.append(r[3] / 10.0)
            n_l.append(r[4])
            p_l.append(r[5])
            k_l.append(r[6])

            time.sleep(SOIL_DELAY)

        moisture = safe_avg(moist)
        soil_temp = safe_avg(temp_s)
        ec = safe_avg(ec_l)
        ph = safe_avg(ph_l)
        nitrogen = safe_avg(n_l)
        phosphorus = safe_avg(p_l)
        potassium = safe_avg(k_l)

        # cache soil
        if moisture is not None:
            last_soil["moisture"] = moisture
        if soil_temp is not None:
            last_soil["temperature"] = soil_temp
        if ec is not None:
            last_soil["ec"] = ec
        if ph is not None:
            last_soil["pH"] = ph
        if nitrogen is not None:
            last_soil["nitrogen"] = nitrogen
        if phosphorus is not None:
            last_soil["phosphorus"] = phosphorus
        if potassium is not None:
            last_soil["potassium"] = potassium

        # DHT read
        air_temp, humidity = read_dht()

        if air_temp is not None:
            last_air_temp = air_temp
        if humidity is not None:
            last_humidity = humidity

        timestamp = datetime.now(timezone.utc)

        reading_payload = {

            "last_seen": timestamp,

            "air_temperature": last_air_temp,
            "humidity": last_humidity,

            "moisture": last_soil["moisture"],
            "temperature": last_soil["temperature"],
            "ec": last_soil["ec"],
            "pH": last_soil["pH"],
            "nitrogen": last_soil["nitrogen"],
            "phosphorus": last_soil["phosphorus"],
            "potassium": last_soil["potassium"],

            "timestamp": timestamp,
            "node_id": NODE_ID,
            "node_name": NODE_NAME,
            "status": "online"
        }

        print_terminal(reading_payload)

        try:

            db.collection("nodes").document(NODE_ID).set({
                "node_name": NODE_NAME,
                "last_seen": timestamp,
                "status": "online",
                "lastReading": reading_payload
            }, merge=True)

            ref = db.collection("readings").document(NODE_ID).collection("history").add(reading_payload)

            print("Firestore: uploaded ✅  doc_id:", ref[1].id)

        except Exception as e:

            print("❌ Firestore upload failed:", repr(e))

        time.sleep(300)

finally:

    client.close()

    try:
        DHT_SENSOR.exit()
    except Exception:
        pass