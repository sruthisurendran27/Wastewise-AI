"""Shared pytest fixtures for the WasteWise backend.

- Uses a dedicated wastewise_test MongoDB database (requires a local Mongo instance).
- Mocks the NVIDIA NIM client so no external API is called during tests.
"""

import json
import os
from pathlib import Path

# Must be set before any app imports so Settings picks them up.
os.environ.setdefault("MONGO_DB_NAME", "wastewise_test")
os.environ.setdefault("NVIDIA_API_KEY", "test-key")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.mongodb import close_db, connect_db, ensure_indexes  # noqa: E402
from app.main import app  # noqa: E402
from app.services import nim_client  # noqa: E402

COLLECTIONS = ["users", "waste_scans", "activities", "diy_ideas_cache", "recyclers", "disposal_guides"]

CANNED_CLASSIFICATION = json.dumps(
    {
        "label": "Plastic Bottle",
        "material": "PET Plastic",
        "category": "Recyclable",
        "condition": "Good for reuse",
        "requires_special_handling": False,
        "confidence": 0.93,
    }
)

CANNED_HAZARD_CLASSIFICATION = json.dumps(
    {
        "label": "Used Battery",
        "material": "Lithium",
        "category": "Hazardous/Special",
        "condition": "Do not open",
        "requires_special_handling": True,
        "confidence": 0.9,
    }
)

CANNED_IDEAS = json.dumps(
    {
        "ideas": [
            {
                "title": "Self-Watering Planter",
                "difficulty": "Easy",
                "time_minutes": 20,
                "extra_materials": "String, soil, seeds",
                "steps": ["Clean the bottle.", "Cut and invert the top.", "Fill with soil and seeds.", "Your planter is ready!"],
                "value_min": 50,
                "value_max": 200,
                "usage_tags": ["Personal use", "Gift"],
            },
            {
                "title": "Pen Holder",
                "difficulty": "Easy",
                "time_minutes": 10,
                "extra_materials": "Scissors, paint",
                "steps": ["Clean the bottle.", "Cut to half height.", "Decorate.", "Use as a desk organiser."],
                "value_min": 20,
                "value_max": 80,
                "usage_tags": ["Personal use"],
            },
        ]
    }
)


@pytest.fixture(autouse=True)
async def fresh_db():
    """Per-test Mongo lifecycle: fresh connected client + empty collections."""
    await close_db()  # ensure we are not reusing a client bound to a previous loop
    db = await connect_db()
    await ensure_indexes()
    for name in COLLECTIONS:
        await db[name].delete_many({})
    yield
    for name in COLLECTIONS:
        await db[name].delete_many({})
    await close_db()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def mock_nim(monkeypatch):
    """Replace the NIM client with a deterministic fake (no network calls)."""

    state = {
        "classification": CANNED_CLASSIFICATION,
        "ideas": CANNED_IDEAS,
        "calls": {"classification": 0, "ideas": 0},
    }

    async def fake_call_vlm(image_data_uri, prompt, max_tokens=512, timeout=60.0):
        if "reuse assistant" in prompt or "ideas" in prompt:
            state["calls"]["ideas"] += 1
            return state["ideas"]
        state["calls"]["classification"] += 1
        return state["classification"]

    monkeypatch.setattr(nim_client, "call_vlm", fake_call_vlm)
    monkeypatch.setattr(nim_client, "NimError", RuntimeError)
    return state


async def register_user(client: AsyncClient, name="Test User", email="tester@example.com", password="secret123"):
    resp = await client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}