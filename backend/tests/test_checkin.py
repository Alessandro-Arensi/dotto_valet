from tests.conftest import auth_headers


async def test_checkin_from_reservation(client, seed_event, operator_token):
    reserve = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Mario", "last_name": "Rossi", "phone": "+393335551111"},
    )
    code = reserve.json()["token"]["code"]

    r = await client.post(
        "/api/checkin",
        json={"token_code": code, "auto_position": True},
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["token"]["code"] == code
    assert body["position"]["slot_number"] == 1


async def test_checkin_walk_in_new_token(client, seed_event, operator_token):
    r = await client.post(
        "/api/checkin",
        json={
            "token_code": "IGNORED",
            "create_token": True,
            "customer_phone": "+393336662222",
            "auto_position": True,
        },
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"]["type"] == "digital"
    assert body["token"]["code"].startswith("DOT-")


async def test_checkin_physical_with_description(client, seed_event, db_session, operator_token):
    from app.models.token import Token
    phys = Token(code="DOT-PHYS", type="physical", status="available", event_id=seed_event.id)
    db_session.add(phys)
    await db_session.commit()

    r = await client.post(
        "/api/checkin",
        json={
            "token_code": "DOT-PHYS",
            "physical_token": True,
            "auto_position": True,
            "bike_description": "Bici rossa con cestino",
        },
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"]["type"] == "physical"


async def test_checkin_no_active_event(client, db_session, operator_token):
    r = await client.post(
        "/api/checkin",
        json={
            "token_code": "IGNORED",
            "create_token": True,
            "customer_phone": "+393339998888",
            "auto_position": True,
        },
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 400
    assert "no active event" in r.json()["detail"].lower()


async def test_checkin_duplicate_customer_by_phone(client, seed_event, operator_token):
    """Reserve online with phone, then operator tries to create_token same phone -> 400."""
    reserve = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={
            "first_name": "Dup",
            "last_name": "Test",
            "phone": "+393334445555",
        },
    )
    assert reserve.status_code == 200

    r = await client.post(
        "/api/checkin",
        json={
            "token_code": "IGNORED",
            "create_token": True,
            "customer_phone": "+393334445555",
            "auto_position": True,
        },
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 400
