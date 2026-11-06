"""Release feature-isolation contract; no live services or databases are touched."""
import asyncio
import pytest
from fastapi import HTTPException

try:
    from backend import server
except ImportError:
    import server

PARKED_PREFIXES = (
    "/api/wallet", "/api/stations", "/api/chargers/", "/api/sessions",
    "/api/owner/", "/api/admin/summary", "/api/admin/chargers",
    "/api/admin/owners", "/api/admin/wallet", "/api/admin/faults",
    "/api/admin/withdrawals", "/api/admin/sessions",
)


def test_parked_routes_have_server_side_guard():
    routes = [route for route in server.app.routes if getattr(route, "path", "").startswith(PARKED_PREFIXES)]
    assert routes, "Expected parked network routes to remain recoverable"
    for route in routes:
        dependencies = getattr(route, "dependant", None)
        assert dependencies is not None
        assert any(d.call is server.require_legacy_network_enabled for d in dependencies.dependencies), route.path


def test_legacy_network_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RUSHX_ENABLE_LEGACY_NETWORK", raising=False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.require_legacy_network_enabled())
    assert exc.value.status_code == 404


def test_legacy_network_requires_explicit_true(monkeypatch):
    monkeypatch.setenv("RUSHX_ENABLE_LEGACY_NETWORK", "yes")
    with pytest.raises(HTTPException):
        asyncio.run(server.require_legacy_network_enabled())
    monkeypatch.setenv("RUSHX_ENABLE_LEGACY_NETWORK", "true")
    assert asyncio.run(server.require_legacy_network_enabled()) is None
