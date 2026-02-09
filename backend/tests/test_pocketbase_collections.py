"""
Test PocketBase: collections, health API, API base.

Verifica che PocketBase sia configurato correttamente con le collections necessarie
(events, tokens, racks, operators) e che l'API risponda correttamente.

Richiede PocketBase in esecuzione (make up-pocketbase).
"""
import pytest
import httpx


class TestPocketBaseHealth:
    """Verifica endpoint health."""

    def test_health_returns_200(self, http_client):
        r = http_client.get("/api/health")
        assert r.status_code == 200

    def test_health_body(self, http_client):
        r = http_client.get("/api/health")
        data = r.json()
        assert data.get("code") == 200 or "healthy" in str(data).lower() or "message" in data


class TestPocketBaseCollections:
    """Verifica che le collection esistano e rispondano."""

    @pytest.mark.parametrize("collection", ["events", "tokens", "racks", "operators"])
    def test_collection_list_returns_200(self, http_client, collection):
        r = http_client.get(f"/api/collections/{collection}/records")
        assert r.status_code == 200, f"{collection}: {r.text}"

    def test_collections_return_items_array(self, http_client):
        for name in ["events", "tokens", "racks", "operators"]:
            r = http_client.get(f"/api/collections/{name}/records")
            data = r.json()
            assert "items" in data
            assert isinstance(data["items"], list)

    def test_events_filter_active(self, http_client):
        r = http_client.get(
            "/api/collections/events/records",
            params={"filter": "(is_active=true)"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        for item in data["items"]:
            assert item.get("is_active") is True
