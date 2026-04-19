async def test_availability_active_event(client, seed_event):
    r = await client.get(f"/api/events/{seed_event.slug}/availability")
    assert r.status_code == 200
    body = r.json()
    assert body["event"]["slug"] == "evento-test"
    assert body["availability"]["total"] == 24
    assert body["can_reserve"] is True


async def test_availability_inactive_event(client, db_session, seed_event):
    seed_event.is_active = False
    await db_session.commit()
    r = await client.get(f"/api/events/{seed_event.slug}/availability")
    assert r.status_code == 404


async def test_reserve_happy_path(client, seed_event):
    r = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Mario", "last_name": "Rossi", "phone": "+393331234567"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["token"]["code"].startswith("DOT-")
    assert body["reservation"]["customer_name"] == "Mario Rossi"


async def test_reserve_without_phone(client, seed_event):
    r = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Luca", "last_name": "Bianchi"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["reservation"]["customer_name"] == "Luca Bianchi"


async def test_reserve_soldout(client, db_session, seed_event):
    seed_event.total_capacity = 1
    await db_session.commit()
    first = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Primo", "last_name": "Test"},
    )
    assert first.status_code == 200
    r = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Secondo", "last_name": "Test"},
    )
    assert r.status_code == 400
    assert "sold out" in r.json()["detail"].lower()


async def test_recover_route_not_shadowed(client, seed_event):
    """Route order check: /recover must not be swallowed by /{code}."""
    r = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Anna", "last_name": "Verdi", "phone": "+393337777777"},
    )
    assert r.status_code == 200
    recover = await client.get("/api/token/recover?phone=+393337777777")
    assert recover.status_code == 200
    body = recover.json()
    assert len(body["tokens"]) == 1


async def test_recover_by_name(client, seed_event):
    await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Giulia", "last_name": "Verdi"},
    )
    r = await client.get("/api/token/recover?last_name=Verdi")
    assert r.status_code == 200
    body = r.json()
    assert any(t["customer_name"] == "Giulia Verdi" for t in body["tokens"])
