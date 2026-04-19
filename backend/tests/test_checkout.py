from tests.conftest import auth_headers


async def test_checkout_digital(client, seed_event, operator_token):
    reserve = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Test", "last_name": "User", "phone": "+393331231234"},
    )
    code = reserve.json()["token"]["code"]

    await client.post(
        "/api/checkin",
        json={"token_code": code, "auto_position": True},
        headers=auth_headers(operator_token),
    )

    r = await client.post(
        "/api/checkout",
        json={"token_code": code},
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["token_type"] == "digital"


async def test_checkout_physical_reusable(client, seed_event, db_session, operator_token):
    """Physical token should be 'available' again after checkout, and re-checkinable."""
    from app.models.token import Token
    phys = Token(code="DOT-REUSE", type="physical", status="available", event_id=seed_event.id)
    db_session.add(phys)
    await db_session.commit()

    await client.post(
        "/api/checkin",
        json={
            "token_code": "DOT-REUSE",
            "physical_token": True,
            "auto_position": True,
            "bike_description": "Bici 1",
        },
        headers=auth_headers(operator_token),
    )

    r = await client.post(
        "/api/checkout",
        json={"token_code": "DOT-REUSE"},
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "physical"

    # Re-checkin same gettone — must succeed (§8.2 fix)
    r2 = await client.post(
        "/api/checkin",
        json={
            "token_code": "DOT-REUSE",
            "physical_token": True,
            "auto_position": True,
            "bike_description": "Bici 2",
        },
        headers=auth_headers(operator_token),
    )
    assert r2.status_code == 200, r2.text


async def test_checkout_already_checked_out(client, seed_event, operator_token):
    reserve = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Already", "last_name": "Out", "phone": "+393338887777"},
    )
    code = reserve.json()["token"]["code"]
    await client.post(
        "/api/checkin",
        json={"token_code": code, "auto_position": True},
        headers=auth_headers(operator_token),
    )
    first = await client.post(
        "/api/checkout",
        json={"token_code": code},
        headers=auth_headers(operator_token),
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/checkout",
        json={"token_code": code},
        headers=auth_headers(operator_token),
    )
    assert second.status_code == 400
