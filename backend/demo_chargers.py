"""Opt-in local/MVP discovery fixtures; these are not real charging locations."""
import math
import os
from datetime import datetime, timezone

DEFAULT_DEMO_CENTER = (28.6271, 77.3654)
# name, distance (km), bearing, connector, price/kWh, power (kW), status
DEMO_SPECS = (
    ("Voltx Sector 62 Hub", 1.5, 20, "Type 2", 15.0, 7.4, "Available"),
    ("Voltx City Center Charger", 2.5, 130, "CCS2", 19.0, 60.0, "Charging"),
    ("Voltx Expressway Point", 4.5, 175, "CCS2", 20.0, 120.0, "Available"),
    ("Voltx Tech Park Station", 6.0, 60, "Type 2", 16.0, 22.0, "Fault"),
    ("Voltx Metro Charge Point", 7.5, 270, "Type 2", 14.0, 11.0, "Offline"),
    ("Voltx Mall Fast Charger", 9.0, 220, "CCS2", 18.0, 60.0, "Available"),
)


def demo_center(environ):
    lat = float(environ.get("DEMO_CUSTOMER_LAT", DEFAULT_DEMO_CENTER[0]))
    lng = float(environ.get("DEMO_CUSTOMER_LNG", DEFAULT_DEMO_CENTER[1]))
    if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("DEMO_CUSTOMER_LAT/LNG must be finite valid coordinates")
    return lat, lng


def destination(lat, lng, distance_km, bearing):
    lat, lng, bearing = map(math.radians, (lat, lng, bearing))
    arc = distance_km / 6371
    end_lat = math.asin(math.sin(lat) * math.cos(arc) + math.cos(lat) * math.sin(arc) * math.cos(bearing))
    end_lng = lng + math.atan2(math.sin(bearing) * math.sin(arc) * math.cos(lat), math.cos(arc) - math.sin(lat) * math.sin(end_lat))
    return round(math.degrees(end_lat), 6), round((math.degrees(end_lng) + 180) % 360 - 180, 6)


async def seed_demo_chargers(db, owner_id, environ=None):
    environ = os.environ if environ is None else environ
    if environ.get("ENABLE_DEMO_CHARGERS", "").lower() != "true":
        return
    lat, lng = demo_center(environ)
    timestamp = datetime.now(timezone.utc).isoformat()
    for index, (name, distance, bearing, connector, price, power, status) in enumerate(DEMO_SPECS, 1):
        cid = f"DEMO{index:06d}"
        station_lat, station_lng = destination(lat, lng, distance, bearing)
        document = {
            "charger_id": cid, "name": name, "owner_id": owner_id,
            "connector": connector, "price_per_kwh": price, "max_power_kw": power,
            "location": "Demo discovery area (simulated location)", "status": status,
            "online": status != "Offline", "lat": station_lat, "lng": station_lng,
            "energy_today": 0.0, "firmware": "v1.6.3", "last_heartbeat": timestamp,
            "created_at": timestamp, "demo": True,
        }
        # Deterministic Mongo _id also prevents duplicates from concurrent startups.
        await db.chargers.update_one(
            {"_id": cid}, {"$setOnInsert": document}, upsert=True
        )
