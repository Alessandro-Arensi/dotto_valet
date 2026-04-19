from tests.conftest import auth_headers


async def test_admin_create_event_requires_admin(client, operator_token):
    r = await client.post(
        "/api/events",
        json={
            "name": "Nuovo",
            "slug": "nuovo",
            "start_date": "2030-01-01T10:00:00+00:00",
            "total_capacity": 50,
        },
        headers=auth_headers(operator_token),
    )
    assert r.status_code == 403


async def test_admin_create_event_happy(client, admin_token):
    r = await client.post(
        "/api/events",
        json={
            "name": "Nuovo",
            "slug": "nuovo",
            "start_date": "2030-01-01T10:00:00+00:00",
            "total_capacity": 50,
        },
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "nuovo"


async def test_admin_create_rack_happy(client, admin_token, seed_event):
    r = await client.post(
        f"/api/events/{seed_event.id}/racks",
        json={"rack_number": 99, "slots": 10, "label": "Test"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text


async def test_admin_delete_rack_blocked_if_active(
    client, admin_token, operator_token, seed_event
):
    list_r = await client.get(
        f"/api/events/{seed_event.id}/racks",
        headers=auth_headers(admin_token),
    )
    racks = list_r.json()
    rack_id = racks[0]["id"]

    reserve = await client.post(
        f"/api/events/{seed_event.slug}/reserve",
        json={"first_name": "Active", "last_name": "Rack"},
    )
    code = reserve.json()["token"]["code"]
    await client.post(
        "/api/checkin",
        json={"token_code": code, "auto_position": True},
        headers=auth_headers(operator_token),
    )

    r = await client.delete(f"/api/racks/{rack_id}", headers=auth_headers(admin_token))
    assert r.status_code == 400


async def test_admin_create_operator(client, admin_token):
    r = await client.post(
        "/api/operators",
        json={
            "name": "Mario",
            "phone": "+393331122334",
            "pin": "9999",
            "is_admin": False,
        },
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Mario"
    assert body["is_admin"] is False


async def test_admin_cannot_deactivate_self(client, admin_token, admin):
    r = await client.delete(
        f"/api/operators/{admin.id}",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 400
