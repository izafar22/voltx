# Local customer-map demo chargers

Opt in in `backend/.env` before starting/restarting the backend:

```dotenv
ENABLE_DEMO_CHARGERS=true
DEMO_CUSTOMER_LAT=28.6271
DEMO_CUSTOMER_LNG=77.3654
```

The coordinates default to the Noida center above when omitted. The backend
never receives browser geolocation for seeding. To test nearby discovery, use a
browser location near this center or configure the seed center near your test
location before the first seed. These are simulated locations, not verified
physical chargers. Leave the flag unset in production.

The existing startup seed supplies the owner. These six additional documents use
stable `DEMO000001` through `DEMO000006` charger IDs and Mongo IDs. Insert-only
upserts preserve statuses, sessions, and coordinates on restart. Changing the
center does not relocate already-seeded documents. Use a fresh development
database to seed a different area. Disabling the flag does not delete fixtures.
The existing `/api/stations` endpoint returns them without frontend changes.

| ID | Name | Distance (straight-line) | Initial status |
| --- | --- | --- | --- |
| DEMO000001 | Voltx Sector 62 Hub | 1.5 km | Available |
| DEMO000002 | Voltx City Center Charger | 2.5 km | Charging |
| DEMO000003 | Voltx Expressway Point | 4.5 km | Available |
| DEMO000004 | Voltx Tech Park Station | 6.0 km | Fault |
| DEMO000005 | Voltx Metro Charge Point | 7.5 km | Offline |
| DEMO000006 | Voltx Mall Fast Charger | 9.0 km | Available |

Run seed unit tests with `python -m pytest tests/test_demo_chargers.py` from
`backend`. Existing API integration tests additionally require the local backend
and MongoDB, with `REACT_APP_BACKEND_URL=http://localhost:8001`.
