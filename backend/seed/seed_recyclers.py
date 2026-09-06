"""Seed the recyclers collection with curated example facilities.

Run from backend/:  python -m seed.seed_recyclers
Idempotent: existing entries with the same name are replaced/upserted.
"""

import asyncio
import sys
from pathlib import Path

# Allow running as `python -m seed.seed_recyclers` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.mongodb import connect_db, close_db, ensure_indexes  # noqa: E402

# Curated sample data centred on Bengaluru (Karnataka, India). Coordinates are
# approximate / illustrative for the demo directory.
RECYCLERS = [
    {
        "name": "EcoGreen Recyclers",
        "type": "Recycler",
        "location": {"type": "Point", "coordinates": [77.5946, 12.9716]},  # lng, lat
        "address": "12, 4th Cross, Koramangala, Bengaluru 560034",
        "accepted_materials": ["PET Plastic", "Plastic", "Paper", "Cardboard", "Glass", "Aluminium"],
        "services": ["Recycling", "Scrap collection"],
        "contact": "+91 98765 43210",
    },
    {
        "name": "GreenPoint Reuse Hub",
        "type": "Collection Centre",
        "location": {"type": "Point", "coordinates": [77.6062, 12.9784]},
        "address": "45, 100 Feet Road, Indiranagar, Bengaluru 560038",
        "accepted_materials": ["PET Plastic", "Plastic", "E-waste", "Cloth"],
        "services": ["Reuse", "Recycling"],
        "contact": "+91 91234 56780",
    },
    {
        "name": "City Scrap Depot",
        "type": "Scrap Dealer",
        "location": {"type": "Point", "coordinates": [77.5800, 12.9600]},
        "address": "3, Wilson Garden, Bengaluru 560030",
        "accepted_materials": ["PET Plastic", "Plastic", "Metal", "Aluminium", "Copper", "Paper"],
        "services": ["Scrap collection", "Buyback"],
        "contact": "+91 90000 12345",
    },
    {
        "name": "WasteCreate Studio",
        "type": "Collection Centre",
        "location": {"type": "Point", "coordinates": [77.6200, 12.9350]},
        "address": "8, Double Road, Jayanagar, Bengaluru 560041",
        "accepted_materials": ["PET Plastic", "Glass", "Cans"],
        "services": ["Reuse", "Recycling"],
        "contact": None,
    },
    {
        "name": "Koramangala Paper Co.",
        "type": "Scrap Dealer",
        "location": {"type": "Point", "coordinates": [77.6080, 12.9350]},
        "address": "21, 5th Block, Koramangala, Bengaluru 560095",
        "accepted_materials": ["Paper", "Cardboard", "Magazines"],
        "services": ["Scrap collection"],
        "contact": "+91 98866 01234",
    },
    {
        "name": "E-Waste Park Collection Centre",
        "type": "Collection Centre",
        "location": {"type": "Point", "coordinates": [77.6300, 12.9500]},
        "address": "Near Ring Road, HSR Layout, Bengaluru 560102",
        "accepted_materials": ["E-waste", "Batteries", "Circuit boards"],
        "services": ["Recycling", "Special handling"],
        "contact": "1800-123-EWASTE",
    },
    {
        "name": "Shubh Metal Recyclers",
        "type": "Recycler",
        "location": {"type": "Point", "coordinates": [77.5700, 12.9750]},
        "address": "77, Peenya Industrial Area, Bengaluru 560058",
        "accepted_materials": ["Aluminium", "Metal", "Copper", "Steel"],
        "services": ["Recycling", "Buyback"],
        "contact": "+91 98450 22334",
    },
    {
        "name": "GlassCycle Hub",
        "type": "Recycler",
        "location": {"type": "Point", "coordinates": [77.6000, 12.9400]},
        "address": "9, Bannerghatta Road, Bengaluru 560076",
        "accepted_materials": ["Glass", "Bottles", "Jars"],
        "services": ["Recycling", "Reuse"],
        "contact": "+91 96322 99001",
    },
    {
        "name": "Battery Beat Collection Point",
        "type": "Collection Centre",
        "location": {"type": "Point", "coordinates": [77.6400, 12.9680]},
        "address": "2, Sarjapur Road, Bengaluru 560102",
        "accepted_materials": ["Batteries", "E-waste", "CFL/LED bulbs"],
        "services": ["Special handling", "Recycling"],
        "contact": "1800-BATTERY",
    },
    {
        "name": "Organic Earth Composting",
        "type": "Collection Centre",
        "location": {"type": "Point", "coordinates": [77.6100, 12.9550]},
        "address": "14, 80 Feet Road, BTM Layout, Bengaluru 560068",
        "accepted_materials": ["Organic waste", "Fruit rinds", "Garden waste"],
        "services": ["Composting", "Reuse"],
        "contact": None,
    },
    {
        "name": "Textile Daan",
        "type": "Recycler",
        "location": {"type": "Point", "coordinates": [77.5850, 12.9700]},
        "address": "5, Assaye Road, Bengaluru 560025",
        "accepted_materials": ["Cloth", "Clothing", "Shoes", "Bags"],
        "services": ["Reuse", "Recycling"],
        "contact": "+91 99008 44556",
    },
]

TAMIL_NADU_SOURCE_URL = "https://www.scrapmonster.com/companies/region/india/tamil-nadu/waste-recycling"


def _directory_record(name, city, district, coordinates, accepted_materials, services):
    """Create a directory-backed record using the listed city as its map area."""
    return {
        "name": name,
        "type": "Recycler",
        "location": {"type": "Point", "coordinates": list(coordinates)},
        "address": f"{city}, Tamil Nadu, India",
        "district": district,
        "accepted_materials": accepted_materials,
        "services": services,
        "contact": None,
        "source_url": TAMIL_NADU_SOURCE_URL,
        "source_note": "Listed in ScrapMonster Tamil Nadu waste and recycling directory",
    }


# City-centre coordinates are deliberately used where the directory does not
# publish a verified street address or facility pin.
RECYCLERS.extend(
    [
        _directory_record("Sunshine Bags", "Tenkasi", "Tenkasi", (77.3152, 8.9591), ["Jute", "Cloth", "Bags"], ["Reuse"]),
        _directory_record("Paradise Wire Recycling Industry", "Chennai", "Chennai", (80.2707, 13.0827), ["Copper", "Metal", "Wire"], ["Recycling", "Scrap collection"]),
        _directory_record("Wingsman Global Trading Pvt Ltd", "Madurai", "Madurai", (78.1198, 9.9252), ["Aluminium", "Copper", "Metal"], ["Recycling", "Scrap collection"]),
        _directory_record("John Plastics", "Nagercoil", "Kanyakumari", (77.4126, 8.1833), ["PET Plastic", "Plastic"], ["Recycling"]),
        _directory_record("RPA Exports and Imports", "Nagercoil", "Kanyakumari", (77.4126, 8.1833), ["PET Plastic", "HDPE Plastic"], ["Recycling"]),
        _directory_record("IRIS Imports & Exports", "Chennai", "Chennai", (80.2707, 13.0827), ["Metal", "Steel"], ["Scrap collection"]),
        _directory_record("ShaalIN (India)", "Chennai", "Chennai", (80.2707, 13.0827), ["Plastic", "Metal"], ["Recycling"]),
        _directory_record("INSCOMI", "Chennai", "Chennai", (80.2707, 13.0827), ["Iron", "Steel", "Metal"], ["Recycling", "Scrap collection"]),
        _directory_record("D Mas Plastic", "Coimbatore", "Coimbatore", (76.9558, 11.0168), ["Plastic", "Plastic scrap"], ["Recycling"]),
        _directory_record("Pearl Enterprise", "Ramanathapuram", "Ramanathapuram", (78.8308, 9.3639), ["Metal", "Mixed scrap"], ["Scrap collection"]),
        _directory_record("GITAM", "Kanyakumari", "Kanyakumari", (77.5385, 8.0883), ["Mixed scrap"], ["Scrap collection"]),
        _directory_record("BN Recycling", "Madurai", "Madurai", (78.1198, 9.9252), ["Metal", "Compressor scrap"], ["Recycling"]),
        _directory_record("Three Star Impex", "Chennai", "Chennai", (80.2707, 13.0827), ["Metal", "Mixed scrap"], ["Scrap collection"]),
        _directory_record("Gudiya Mobiles Private Limited", "Chennai", "Chennai", (80.2707, 13.0827), ["E-waste", "Mobile phones"], ["E-waste recycling"]),
        _directory_record("Kwality", "Chennai", "Chennai", (80.2707, 13.0827), ["Paper", "Paper scrap"], ["Recycling"]),
        _directory_record("Vishnu Polymer Industries", "Coimbatore", "Coimbatore", (76.9558, 11.0168), ["Plastic", "LDPE Plastic"], ["Recycling"]),
        _directory_record("SRK Traders and Services", "Arni", "Tiruvannamalai", (79.2850, 12.6670), ["Ceramic", "Electronic scrap"], ["Scrap collection"]),
        _directory_record("Mohamed Traders", "Chennai", "Chennai", (80.2707, 13.0827), ["Mixed scrap", "Metal", "Paper"], ["Scrap collection"]),
        _directory_record("Madras Enterprises", "Chennai", "Chennai", (80.2707, 13.0827), ["Cardboard", "Paper"], ["Recycling"]),
        _directory_record("Enviro Metals Recyclers Pvt Ltd", "Chennai", "Chennai", (80.2707, 13.0827), ["Aluminium", "E-waste", "Metal"], ["Recycling", "Waste management"]),
        _directory_record("VSB Plastics", "Coimbatore", "Coimbatore", (76.9558, 11.0168), ["Plastic", "PP Plastic"], ["Recycling"]),
    ]
)


async def seed_recyclers(db) -> int:
    """Upsert the curated recycler directory into an existing database."""
    collection = db["recyclers"]

    for rec in RECYCLERS:
        result = await collection.replace_one(
            {"name": rec["name"]}, rec, upsert=True
        )
        print(f"  {'upserted' if result.upserted_id else 'updated'} {rec['name']}")

    return await collection.count_documents({})


async def run() -> None:
    db = await connect_db()
    await ensure_indexes()
    count = await seed_recyclers(db)
    print(f"Seed complete. recyclers collection now has {count} entries.")

    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
