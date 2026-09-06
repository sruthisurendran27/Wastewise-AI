"""Tests for the scan upload / classify / correct flow (NIM mocked)."""

import io

from tests.conftest import CANNED_HAZARD_CLASSIFICATION, auth_headers, register_user


def _png_bytes() -> bytes:
    """A tiny valid 2x2 PNG for upload tests."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(128, 200, 60)).save(buf, format="PNG")
    return buf.getvalue()


async def _upload(client, token, payload: bytes = None) -> dict:
    files = {"file": ("waste.png", payload or _png_bytes(), "image/png")}
    resp = await client.post("/api/scan", files=files, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_upload_classifies_waste(client, mock_nim):
    token = (await register_user(client))["access_token"]
    scan = await _upload(client, token)

    assert scan["ai_result"]["label"] == "Plastic Bottle"
    assert scan["ai_result"]["material"] == "PET Plastic"
    assert scan["ai_result"]["category"] == "Recyclable"
    assert scan["final_label"] == "Plastic Bottle"
    assert scan["requires_special_handling"] is False
    assert scan["status"] == "analyzed"
    assert scan["image_url"].startswith("/uploads/")


async def test_hazard_keyword_safety_net(client, mock_nim):
    """A battery must always be flagged for special handling."""
    token = (await register_user(client))["access_token"]
    mock_nim["classification"] = CANNED_HAZARD_CLASSIFICATION
    scan = await _upload(client, token)

    assert scan["ai_result"]["label"] == "Used Battery"
    assert scan["requires_special_handling"] is True
    assert scan["category"] == "Hazardous/Special"


async def test_upload_requires_auth(client):
    files = {"file": ("waste.png", _png_bytes(), "image/png")}
    resp = await client.post("/api/scan", files=files)
    assert resp.status_code == 401


async def test_get_scan_ownership(client):
    token = (await register_user(client))["access_token"]
    scan = await _upload(client, token)

    # Owner can fetch
    resp = await client.get(f"/api/scan/{scan['id']}", headers=auth_headers(token))
    assert resp.status_code == 200

    # Another user cannot fetch this scan
    other = (await register_user(client, email="other@example.com"))["access_token"]
    resp = await client.get(f"/api/scan/{scan['id']}", headers=auth_headers(other))
    assert resp.status_code == 404


async def test_manual_correction(client):
    token = (await register_user(client))["access_token"]
    scan = await _upload(client, token)

    resp = await client.patch(
        f"/api/scan/{scan['id']}/correct",
        json={"label": "Glass Jar", "category": "Recyclable", "material": "Glass"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_label"] == "Glass Jar"
    assert body["user_corrected_label"] == "Glass Jar"
    assert body["ai_result"]["label"] == "Glass Jar"