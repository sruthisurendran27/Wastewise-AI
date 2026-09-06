"""Tests for points, activity endpoints, and the dashboard aggregation."""

import io

from PIL import Image

from tests.conftest import auth_headers, register_user


async def _upload_scan(client, token, color=(60, 120, 200)):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=color).save(buf, format="PNG")
    files = {"file": ("waste.png", buf.getvalue(), "image/png")}
    resp = await client.post("/api/scan", files=files, headers=auth_headers(token))
    assert resp.status_code == 201
    return resp.json()


async def _do(client, token, action, scan_id, **params):
    return await client.post(
        f"/api/activity/{action}?scan_id={scan_id}&" +
        "&".join(f"{k}={v}" for k, v in params.items()),
        headers=auth_headers(token),
    )


async def test_made_item_awards_points_and_value(client):
    token = (await register_user(client))["access_token"]
    scan = await _upload_scan(client, token)

    resp = await _do(client, token, "made", scan["id"], value_min=50, value_max=200)
    assert resp.status_code == 200
    assert resp.json()["points_earned"] == 20

    dashboard = await client.get("/api/dashboard", headers=auth_headers(token))
    stats = dashboard.json()
    assert stats["points"] == 20
    assert stats["items_reused"] == 1
    assert stats["waste_diverted"] == 1
    assert stats["value_created_total_min"] == 50
    assert stats["value_created_total_max"] == 200
    assert len(stats["recent_activities"]) == 1


async def test_recycled_item_awards_points(client):
    token = (await register_user(client))["access_token"]
    scan = await _upload_scan(client, token)

    resp = await _do(client, token, "recycled", scan["id"])
    assert resp.status_code == 200
    assert resp.json()["points_earned"] == 15

    dashboard = (await client.get("/api/dashboard", headers=auth_headers(token))).json()
    assert dashboard["points"] == 15
    assert dashboard["items_recycled"] == 1
    assert dashboard["waste_diverted"] == 1


async def test_no_double_crediting_same_scan(client):
    token = (await register_user(client))["access_token"]
    scan = await _upload_scan(client, token)

    first = await _do(client, token, "made", scan["id"])
    assert first.status_code == 200

    second = await _do(client, token, "made", scan["id"])
    assert second.status_code == 409

    dashboard = (await client.get("/api/dashboard", headers=auth_headers(token))).json()
    assert dashboard["items_reused"] == 1


async def test_disposal_guide_lookup(client):
    from app.db.mongodb import get_db

    db = get_db()
    await db["disposal_guides"].insert_one(
        {
            "waste_type": "Battery",
            "hazard_level": "High",
            "instructions": ["Never throw in regular trash."],
            "special_collection_required": True,
            "notes": "Test note",
        }
    )
    token = (await register_user(client))["access_token"]
    resp = await client.get("/api/disposal?waste_type=Battery", headers=auth_headers(token))
    assert resp.status_code == 200
    guides = resp.json()["guides"]
    assert len(guides) == 1
    assert guides[0]["hazard_level"] == "High"


async def test_disposal_guide_missing(client):
    token = (await register_user(client))["access_token"]
    resp = await client.get("/api/disposal?waste_type=NoSuchThing", headers=auth_headers(token))
    assert resp.status_code == 404