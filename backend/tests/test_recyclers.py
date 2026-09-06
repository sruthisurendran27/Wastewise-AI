"""Tests for geographic recycler search against the seeded directory."""

from bson import ObjectId

from app.db.mongodb import get_db
from tests.conftest import auth_headers, register_user

# Koramangala, Bengaluru: center point used by tests.
CENTER_LAT, CENTER_LNG = 12.9716, 77.5946


async def _seed_recyclers():
    db = get_db()
    docs = [
        {
            "_id": ObjectId("000000000000000000000001"),
            "name": "Recycler A",
            "type": "Recycler",
            "location": {"type": "Point", "coordinates": [CENTER_LNG + 0.01, CENTER_LAT]},
            "address": "1, Test Street",
            "accepted_materials": ["PET Plastic", "Paper"],
            "services": ["Recycling"],
            "contact": "+91 11111 11111",
        },
        {
            "_id": ObjectId("000000000000000000000002"),
            "name": "Collection Centre B",
            "type": "Collection Centre",
            "location": {"type": "Point", "coordinates": [CENTER_LNG + 0.03, CENTER_LAT]},
            "address": "2, Test Street",
            "accepted_materials": ["PET Plastic", "E-waste"],
            "services": ["Reuse"],
            "contact": None,
        },
        {
            "_id": ObjectId("000000000000000000000003"),
            "name": "Scrap Dealer C",
            "type": "Scrap Dealer",
            "location": {"type": "Point", "coordinates": [CENTER_LNG + 0.02, CENTER_LAT]},
            "address": "3, Test Street",
            "accepted_materials": ["Paper"],
            "services": ["Scrap collection"],
            "contact": "+91 33333 33333",
        },
    ]
    await db["recyclers"].insert_many(docs)


async def test_nearby_recyclers_sorted_by_distance(client):
    await _seed_recyclers()
    token = (await register_user(client))["access_token"]

    resp = await client.get(
        f"/api/recyclers/nearby?lat={CENTER_LAT}&lng={CENTER_LNG}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 3
    # Nearest first.
    distances = [r["distance_km"] for r in results]
    assert distances == sorted(distances)
    assert results[0]["name"] == "Recycler A"


async def test_filter_by_accepted_material(client):
    await _seed_recyclers()
    token = (await register_user(client))["access_token"]

    resp = await client.get(
        f"/api/recyclers/nearby?lat={CENTER_LAT}&lng={CENTER_LNG}&material=PET%20Plastic",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert {r["name"] for r in results} == {"Recycler A", "Collection Centre B"}


async def test_filter_by_facility_type(client):
    await _seed_recyclers()
    token = (await register_user(client))["access_token"]

    resp = await client.get(
        f"/api/recyclers/nearby?lat={CENTER_LAT}&lng={CENTER_LNG}&facility_type=Scrap%20Dealer",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["name"] == "Scrap Dealer C"


async def test_recycler_filters_metadata(client):
    await _seed_recyclers()
    token = (await register_user(client))["access_token"]

    resp = await client.get("/api/recyclers/filters", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "PET Plastic" in body["materials"]
    assert "Recycler" in body["types"]