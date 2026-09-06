"""Tests for DIY suggestion generation and caching."""

from tests.conftest import CANNED_HAZARD_CLASSIFICATION, auth_headers, register_user


async def _upload_scan(client, token):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(70, 120, 200)).save(buf, format="PNG")
    files = {"file": ("waste.png", buf.getvalue(), "image/png")}
    resp = await client.post("/api/scan", files=files, headers=auth_headers(token))
    assert resp.status_code == 201
    return resp.json()


async def test_get_create_ideas(client, mock_nim):
    token = (await register_user(client))["access_token"]
    scan = await _upload_scan(client, token)

    resp = await client.get(f"/api/scan/{scan['id']}/ideas", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["label"] == "Plastic Bottle"
    assert len(body["ideas"]) == 2
    assert body["ideas"][0]["title"] == "Self-Watering Planter"
    assert body["ideas"][0]["is_best_match"] is True
    assert body["ideas"][0]["value_min"] == 50
    assert body["ideas"][0]["steps"]


async def test_ideas_cached_after_first_call(client, mock_nim):
    token = (await register_user(client))["access_token"]
    scan = await _upload_scan(client, token)

    # First call hits NIM and populates the cache.
    resp1 = await client.get(f"/api/scan/{scan['id']}/ideas", headers=auth_headers(token))
    assert resp1.status_code == 200
    assert mock_nim["calls"]["ideas"] == 1

    # Second call for the same label comes from cache - no extra NIM call.
    resp2 = await client.get(f"/api/scan/{scan['id']}/ideas", headers=auth_headers(token))
    assert resp2.status_code == 200
    assert mock_nim["calls"]["ideas"] == 1
    assert resp2.json() == resp1.json()


async def test_no_ideas_for_hazardous_item(client, mock_nim):
    """Items flagged for special handling must never get DIY ideas."""
    token = (await register_user(client))["access_token"]
    mock_nim["classification"] = CANNED_HAZARD_CLASSIFICATION

    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 70, 70)).save(buf, format="PNG")
    files = {"file": ("waste.png", buf.getvalue(), "image/png")}
    resp = await client.post("/api/scan", files=files, headers=auth_headers(token))
    scan = resp.json()

    resp = await client.get(f"/api/scan/{scan['id']}/ideas", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["ideas"] == []
    assert mock_nim["calls"]["ideas"] == 0