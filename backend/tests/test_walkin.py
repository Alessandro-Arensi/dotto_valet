async def test_walkin_happy(client, seed_event):
    r = await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "Mario", "last_name": "Rossi"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["token"]["code"].startswith("DOT-")
    assert body["position"]["slot_number"] == 1
    assert body["position"]["rack_number"] == 1
    assert body["customer_name"] == "Mario Rossi"


async def test_walkin_assigns_next_free_slot(client, seed_event):
    await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "A", "last_name": "Uno"},
    )
    r2 = await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "B", "last_name": "Due"},
    )
    assert r2.status_code == 200
    assert r2.json()["position"]["slot_number"] == 2


async def test_walkin_event_not_found(client):
    r = await client.post(
        "/api/events/non-existent/walkin",
        json={"first_name": "X", "last_name": "Y"},
    )
    assert r.status_code == 404


async def test_walkin_requires_names(client, seed_event):
    r = await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "", "last_name": "Rossi"},
    )
    assert r.status_code == 422


async def test_walkin_sold_out(client, db_session, seed_event):
    seed_event.total_capacity = 1
    await db_session.commit()
    first = await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "Primo", "last_name": "Test"},
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/events/{seed_event.slug}/walkin",
        json={"first_name": "Secondo", "last_name": "Test"},
    )
    assert second.status_code == 400
