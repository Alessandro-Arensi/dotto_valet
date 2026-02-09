"""
Fixture condivise per test PocketBase (collections, hooks).
Richiedono PocketBase in esecuzione (es. make up-pocketbase).
Per i test degli hook che creano/aggiornano token serve auth admin:
  PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD (superuser creato da Admin UI o superuser upsert).
  Puoi metterle nel file .env alla root del progetto.
"""
import os
from pathlib import Path

import pytest
import httpx

# Carica .env dalla root del progetto (se esiste) per PB_ADMIN_* e POCKETBASE_URL
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

# URL PocketBase (override con POCKETBASE_URL nel .env)
PB_URL = os.environ.get("POCKETBASE_URL", "http://localhost:8090").rstrip("/")
TIMEOUT = 10.0
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "")


def _pb_available() -> bool:
    try:
        r = httpx.get(f"{PB_URL}/api/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _admin_token() -> str | None:
    if not PB_ADMIN_EMAIL or not PB_ADMIN_PASSWORD:
        return None
    try:
        # PocketBase superuser auth: collection _superusers
        r = httpx.post(
            f"{PB_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASSWORD},
            timeout=5.0,
        )
        if r.status_code != 200:
            return None
        return r.json().get("token")
    except Exception:
        return None


@pytest.fixture(scope="session")
def pb_url():
    """URL base API PocketBase."""
    return PB_URL


@pytest.fixture(scope="session")
def pb_available(pb_url):
    """True se PocketBase risponde su pb_url."""
    return _pb_available()


@pytest.fixture(scope="session")
def http_client(pb_available):
    """Client HTTP per chiamate all'API PocketBase (senza auth)."""
    if not pb_available:
        pytest.skip("PocketBase non raggiungibile: avvia con make up-pocketbase")
    return httpx.Client(base_url=PB_URL, timeout=TIMEOUT)


@pytest.fixture(scope="session")
def http_client_admin(http_client, pb_available):
    """
    Client HTTP con auth admin (superuser).
    Necessario per creare/aggiornare token (test hook PocketBase).
    Se PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD non sono impostati o il login fallisce,
    restituisce None e i test che lo usano faranno skip.
    """
    if not pb_available:
        return None
    token = _admin_token()
    if not token:
        return None
    return httpx.Client(
        base_url=PB_URL,
        timeout=TIMEOUT,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def first_active_event_id(http_client, http_client_admin):
    """
    ID del primo evento attivo (per test che creano token).
    Se non esiste nessun evento, prova a crearne uno automaticamente (richiede auth admin).
    Se anche la creazione fallisce, il test viene skippato.
    """
    r = http_client.get(
        "/api/collections/events/records",
        params={"filter": "(is_active=true)", "perPage": 1},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or []
    if items:
        return items[0]["id"]
    
    # Nessun evento attivo: prova a crearne uno automaticamente se abbiamo auth admin
    if http_client_admin:
        try:
            from datetime import datetime, timedelta
            import random
            
            # Crea un evento di test
            test_event = {
                "name": f"Test Event {random.randint(1000, 9999)}",
                "slug": f"test-event-{int(datetime.now().timestamp())}",
                "location": "Test Location",
                "start_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "end_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "total_capacity": 100,
                "slots_available": 100,
                "is_active": True,
            }
            r_create = http_client_admin.post(
                "/api/collections/events/records",
                json=test_event,
            )
            if r_create.status_code in (200, 201):
                return r_create.json()["id"]
        except Exception:
            pass
    
    pytest.skip("Nessun evento attivo: crea un evento dalla Admin UI o imposta PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD per creazione automatica")


@pytest.fixture
def event_with_slots(http_client, first_active_event_id):
    """
    Dati del primo evento attivo con slots_available > 0.
    Se slots_available è 0, il test viene skippato.
    """
    r = http_client.get(f"/api/collections/events/records/{first_active_event_id}")
    assert r.status_code == 200, r.text
    record = r.json()
    if (record.get("slots_available") or 0) < 1:
        pytest.skip("Evento senza slot disponibili: usa un evento con slots_available >= 1")
    return record
