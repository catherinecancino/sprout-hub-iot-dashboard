import time
from datetime import datetime, timezone

from pymodbus.client import ModbusSerialClient
import adafruit_dht
from adafruit_blinka.microcontroller.bcm283x import pin

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# Firestore settings
# -------------------------
PROJECT_ID = "agritech-iot-847f1"
SERVICE_KEY = "serviceAccountKey.json"
DEVICE_NAME = "uno-pi"         # change if you want
COLLECTION = "sensor_readings" # history collection

# Initialize Firebase once
cred = credentials.Certificate(SERVICE_KEY)
firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
db = firestore.client()

# -------------------------
# RS485 / Modbus settings
# -------------------------
PORT = "/dev/ttyUSB0"   # change if needed
BAUD = 4800             # default from manual
SLAVE_ID = 1

SOIL_SAMPLES = 10       # how many soil readings to average
SOIL_DELAY = 1          # seconds between soil samples

# -------------------------
# DHT settings
# -------------------------
DHT_SENSOR = adafruit_dht.DHT11(pin.D17, use_pulseio=False)  # you said DHT11 works on GPIO17
DHT_WARMUP_SEC = 2

# -------------------------
# Helpers
# -------------------------
def int16_signed(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x

def safe_avg(values):
    return (sum(values) / len(values)) if values else None

def read_dht():
    """Return (temp_c, humidity) or (None, None) if read fails."""
    try:
        t = DHT_SENSOR.temperature
        h = DHT_SENSOR.humidity
        if t is None or h is None:
            return None, None
        return float(t), float(h)
    except RuntimeError:
        return None, None

# -------------------------
# Main
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
    raise SystemExit(f"Could not open {PORT}. Check adapter/port and permissions.")

time.sleep(DHT_WARMUP_SEC)

try:
    while True:
        print("\nCollecting samples... (CTRL+C to stop)")

        moist_list, temp_list, ec_list, ph_list = [], [], [], []
        n_list, p_list, k_list = [], [], []
        sal_list, tds_list = [], []

        # Collect soil samples
        for i in range(SOIL_SAMPLES):
            resp = client.read_holding_registers(address=0x0000, count=9, slave=SLAVE_ID)
            if resp.isError():
                print("Modbus error:", resp)
                break

            r = resp.registers

            moist_list.append(r[0] / 10.0)
            temp_list.append(int16_signed(r[1]) / 10.0)
            ec_list.append(r[2])
            ph_list.append(r[3] / 10.0)

            n_list.append(r[4])
            p_list.append(r[5])
            k_list.append(r[6])

            sal_list.append(r[7])
            tds_list.append(r[8])

            time.sleep(SOIL_DELAY)

        # Average soil readings
        moisture = safe_avg(moist_list)
        soil_temp = safe_avg(temp_list)
        ec = safe_avg(ec_list)
        ph = safe_avg(ph_list)
        n = safe_avg(n_list)
        p = safe_avg(p_list)
        k = safe_avg(k_list)
        sal = safe_avg(sal_list)
        tds = safe_avg(tds_list)

        # Read DHT a few times quickly and take first valid
        air_t, air_h = None, None
        for _ in range(5):
            air_t, air_h = read_dht()
            if air_t is not None and air_h is not None:
                break
            time.sleep(0.5)

        print("\n====== Averaged Readings ======")

        if moisture is None:
            print("Soil: (no valid readings)")
        else:
            print("Soil (RS485):")
            print(f"  Moisture:  {moisture:.1f} %")
            print(f"  Temp:      {soil_temp:.1f} °C")
            print(f"  EC:        {ec:.0f} µS/cm")
            print(f"  pH:        {ph:.1f}")
            print(f"  N:         {n:.0f}")
            print(f"  P:         {p:.0f}")
            print(f"  K:         {k:.0f}")
            print(f"  Salinity*: {sal:.0f}")
            print(f"  TDS*:      {tds:.0f}")
            print("  *Salinity/TDS are reference values in many manuals.")

        print("\nAir (DHT on GPIO17):")
        if air_t is None:
            print("  (no valid DHT reading)")
        else:
            print(f"  Temp:      {air_t:.1f} °C")
            print(f"  Humidity:  {air_h:.1f} %")

        # -------------------------
        # Firestore upload
        # -------------------------
        payload = {
            "timestamp": datetime.now(timezone.utc),
            "device": DEVICE_NAME,
            "soil": {
                "moisture_pct": moisture,
                "temp_c": soil_temp,
                "ec_us_cm": ec,
                "ph": ph,
                "n": n,
                "p": p,
                "k": k,
                "salinity_ref": sal,
                "tds_ref": tds
            },
            "air": {
                "temp_c": air_t,
                "humidity_pct": air_h
            }
        }

        try:
            # 1) Append to history
            db.collection(COLLECTION).add(payload)

            # 2) Also keep latest snapshot (optional but super useful)
            db.collection("devices").document(DEVICE_NAME).set(payload)

            print("\nFirestore: uploaded ✅")
        except Exception as e:
            print("\nFirestore upload failed:", e)

        print("==============================")

        time.sleep(2)

finally:
    client.close()
    try:
        DHT_SENSOR.exit()
    except Exception:
        pass
