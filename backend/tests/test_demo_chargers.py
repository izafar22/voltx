import asyncio
import math
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from demo_chargers import DEFAULT_DEMO_CENTER, DEMO_SPECS, demo_center, seed_demo_chargers


class Chargers:
    def __init__(self):
        self.documents = {}

    async def update_one(self, query, update, upsert):
        assert upsert is True
        assert set(update) == {"$setOnInsert"}
        self.documents.setdefault(query["_id"], {**query, **update["$setOnInsert"]})


def seed(collection, config):
    asyncio.run(seed_demo_chargers(SimpleNamespace(chargers=collection), "owner-demo", config))


def test_seed_once_preserves_existing_state():
    chargers = Chargers()
    config = {"ENABLE_DEMO_CHARGERS": "true"}
    seed(chargers, config)
    assert len(chargers.documents) == 6
    chargers.documents["DEMO000001"]["status"] = "Charging"
    original = {key: dict(value) for key, value in chargers.documents.items()}
    seed(chargers, config)
    assert chargers.documents == original


@pytest.mark.parametrize("center", [DEFAULT_DEMO_CENTER, (19.076, 72.8777)])
def test_valid_coordinates_distances_and_status_mix(center):
    chargers = Chargers()
    seed(chargers, {"ENABLE_DEMO_CHARGERS": "true", "DEMO_CUSTOMER_LAT": str(center[0]), "DEMO_CUSTOMER_LNG": str(center[1])})
    for doc, spec in zip(chargers.documents.values(), DEMO_SPECS):
        assert -90 <= doc["lat"] <= 90 and -180 <= doc["lng"] <= 180
        lat1, lat2 = map(math.radians, (center[0], doc["lat"]))
        dlat, dlng = math.radians(doc["lat"] - center[0]), math.radians(doc["lng"] - center[1])
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        distance = 6371 * 2 * math.asin(math.sqrt(a))
        assert distance == pytest.approx(spec[1], abs=.001)
        assert distance < 10
        assert doc["owner_id"] == "owner-demo"
        assert doc["online"] == (doc["status"] != "Offline")
    assert [d["status"] for d in chargers.documents.values()] == ["Available", "Charging", "Available", "Fault", "Offline", "Available"]


def test_disabled_by_default():
    collection = SimpleNamespace(update_one=AsyncMock())
    seed(collection, {})
    collection.update_one.assert_not_called()


@pytest.mark.parametrize("lat,lng", [("nan", "77"), ("91", "77"), ("28", "181"), ("abc", "77")])
def test_invalid_config(lat, lng):
    with pytest.raises(ValueError):
        demo_center({"DEMO_CUSTOMER_LAT": lat, "DEMO_CUSTOMER_LNG": lng})
