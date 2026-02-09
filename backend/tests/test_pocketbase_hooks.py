"""
Test PocketBase: hook JavaScript per validazione foto token fisici.

NOTA: Il decremento slot NON viene testato qui perché non può essere implementato negli hook
PocketBase (causa 400). Il decremento slot verrà testato quando implementiamo l'endpoint
FastAPI di check-in.

Richiede PocketBase in esecuzione e auth admin (PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD).
"""
import random
import time
import pytest


def _token_code():
    return f"DOT-T{int(time.time_ns() % 100000):05d}-{random.randint(100, 999)}"


def _email():
    return f"test-{time.time_ns()}-{random.randint(100000, 999999)}@example.com"


# Payload minimo per creare un token (campi obbligatori; PocketBase accetta bool true)
def _token_payload(event_id, token_code=None, email=None, token_type="digital", status="pending"):
    return {
        "event": event_id,
        "email": email or _email(),
        "token_code": token_code or _token_code(),
        "token_type": token_type,
        "status": status,
        "newsletter_opt_in": True,
        "whatsapp_sent": True,
    }


def _client_or_skip(http_client_admin):
    if http_client_admin is None:
        pytest.skip(
            "Test hook PocketBase richiedono auth admin: imposta PB_ADMIN_EMAIL e PB_ADMIN_PASSWORD"
        )
    return http_client_admin


class TestPocketBaseHooksPhotoValidation:
    """Hook: foto obbligatoria per token_type=physical."""

    def test_create_physical_token_without_photo_rejected(
        self, http_client_admin, first_active_event_id
    ):
        client = _client_or_skip(http_client_admin)
        r = client.post(
            "/api/collections/tokens/records",
            json=_token_payload(
                first_active_event_id, token_type="physical", status="pending"
            ),
        )
        assert r.status_code == 400
        data = r.json()
        msg = (data.get("message") or data.get("data", {}).get("message") or "").lower()
        assert "foto" in msg or "photo" in msg or "obbligatoria" in msg

    def test_create_digital_token_without_photo_accepted(
        self, http_client_admin, first_active_event_id
    ):
        client = _client_or_skip(http_client_admin)
        r = client.post(
            "/api/collections/tokens/records",
            json=_token_payload(first_active_event_id, token_type="digital", status="pending"),
        )
        assert r.status_code in (200, 201), (
            f"Create digital token: {r.status_code} {r.text}"
        )
        data = r.json()
        assert data.get("token_type") == "digital"

    def test_update_physical_token_without_photo_rejected(
        self, http_client_admin, first_active_event_id
    ):
        """Hook: foto obbligatoria anche per update di token fisici."""
        client = _client_or_skip(http_client_admin)
        # Crea un token digital (senza foto)
        r = client.post(
            "/api/collections/tokens/records",
            json=_token_payload(first_active_event_id, token_type="digital", status="pending"),
        )
        assert r.status_code in (200, 201), f"Create digital token: {r.status_code} {r.text}"
        token_id = r.json()["id"]
        
        # Prova a cambiare a physical senza aggiungere foto (deve fallire)
        r2 = client.patch(
            f"/api/collections/tokens/records/{token_id}",
            json={"token_type": "physical"},
        )
        assert r2.status_code == 400, f"Update to physical without photo should fail: {r2.status_code} {r2.text}"
        data = r2.json()
        msg = (data.get("message") or data.get("data", {}).get("message") or "").lower()
        assert "foto" in msg or "photo" in msg or "obbligatoria" in msg
