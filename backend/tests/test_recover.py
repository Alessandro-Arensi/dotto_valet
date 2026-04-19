async def test_recover_happy_by_phone(client, seed_event):
    await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Lost", "last_name": "Phone", "phone": "+393334321234"},
    )
    r = await client.get("/api/token/recover?phone=+393334321234")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert len(body["tokens"]) == 1


async def test_recover_happy_by_name(client, seed_event):
    await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Anna", "last_name": "Rossi"},
    )
    r = await client.get("/api/token/recover?first_name=Anna&last_name=Rossi")
    assert r.status_code == 200
    assert len(r.json()["tokens"]) == 1


async def test_recover_disambiguates_homonyms(client, seed_event):
    """Two customers with same name. Operator needs position + check-in time to pick."""
    await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "Mario", "last_name": "Rossi"},
    )
    await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "Mario", "last_name": "Rossi"},
    )
    r = await client.get("/api/token/recover?last_name=Rossi")
    assert r.status_code == 200
    tokens = r.json()["tokens"]
    assert len(tokens) == 2
    # Each token must carry disambiguation data
    for t in tokens:
        assert t["customer_name"] == "Mario Rossi"
        assert t["checked_in_at"] is not None
        assert t["position"] is not None
        assert t["position"]["slot_number"] >= 1
    # Slot numbers differ
    slots = {t["position"]["slot_number"] for t in tokens}
    assert len(slots) == 2


async def test_recover_includes_phone_masked(client, seed_event):
    await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Luca", "last_name": "Bianchi", "phone": "+393335554444"},
    )
    r = await client.get("/api/token/recover?last_name=Bianchi")
    assert r.status_code == 200
    token = r.json()["tokens"][0]
    assert token["phone_masked"] is not None
    assert "****" in token["phone_masked"]


async def test_recover_requires_some_filter(client):
    r = await client.get("/api/token/recover")
    assert r.status_code == 400


async def test_recover_unknown(client):
    r = await client.get("/api/token/recover?phone=+393337654321")
    assert r.status_code == 404


async def test_recover_only_active_tokens(client, seed_event, db_session):
    """Recover must skip checked_out / expired / lost tokens."""
    from app.models.customer import Customer
    from app.models.token import Token
    from datetime import datetime, timezone

    customer = Customer(
        first_name="Chiuso",
        last_name="Ticket",
        phone="+393332223333",
        phone_normalized="+393332223333",
    )
    db_session.add(customer)
    await db_session.flush()

    closed = Token(
        code="DOT-CLOS",
        type="digital",
        status="checked_out",
        event_id=seed_event.id,
        customer_id=customer.id,
        reserved_at=datetime.now(timezone.utc),
    )
    db_session.add(closed)
    await db_session.commit()

    r = await client.get("/api/token/recover?phone=+393332223333")
    assert r.status_code == 404
