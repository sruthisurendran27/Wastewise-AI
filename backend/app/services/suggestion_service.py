"""DIY suggestion service: generate personalized 'create value' ideas from the NIM VLM.

Ideas are cached per final_label in the diy_ideas_cache collection so repeat scans of
the same material don't trigger new (paid) model calls.
"""

import json
import re
from typing import List, Optional

from app.models.waste_scan import AIClassification
from app.services import nim_client

SLUG_RE = re.compile(r"[^a-z0-9]+")
SPECIAL_HANDLING_TERMS = (
    "battery", "e-waste", "electronic", "phone", "mobile", "smartphone",
    "cellphone", "circuit", "chemical", "medicine", "syringe", "bulb",
    "aerosol", "gas cylinder", "oil",
)

SUGGESTION_PROMPT_TPL = """You are WasteWise, a safe waste-reuse and value-recovery assistant.
The identified waste product is "{label}". Its material is "{material}" and its category is "{category}".
The product/object is the primary subject of every suggestion. Use the material only to
check safety, durability, cleaning, and feasibility. Do not replace the product with a
generic material idea and never assume it is a plastic bottle.

Check one thing first: if this item requires special handling (batteries, e-waste, chemicals,
medicines, sharps, bulbs, aerosol cans, etc.) then respond with exactly:
{{"ideas": []}}

For Organic/Compostable waste, suggest recovery ideas such as home composting, leaf mould,
or natural soil amendment. Do not suggest crafts using rotting food, and do not recommend
composting meat, dairy, oils, diseased plants, or chemically treated material unless the
user confirms their compost system accepts it. For clean reusable or recyclable materials,
propose 3 practical ideas specifically for reusing or recovering the identified product.
Respond with ONLY a JSON object:
{{
  "ideas": [
    {{
      "title": "Short idea name",
      "difficulty": "Easy|Medium|Hard",
      "time_minutes": 15,
      "extra_materials": "Short list of common extra materials",
      "steps": ["Step 1 ...", "Step 2 ...", "Step 3 ..."],
      "value_min": 20,
      "value_max": 150,
      "usage_tags": ["Personal use", "Gift", "Sell"]
    }}
  ]
}}
Rules:
- Steps must be safe, practical, and specific to the "{label}" product.
- Do not suggest opening, cutting, burning, puncturing, or modifying hazardous products.
- value_min/value_max are Rs (Indian Rupees) the finished item might be worth.
- Do not suggest cutting, burning, or handling anything dangerous.
"""


def _slugify(title: str) -> str:
    slug = SLUG_RE.sub("-", title.lower()).strip("-")
    return slug or "idea"


def _parse_ideas(raw: str, label: str, material: str) -> List[dict]:
    """Parse the model JSON output into the DiyIdea response shape."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            # If the model failed, return an empty list; callers handle it gracefully.
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []

    raw_ideas = data.get("ideas", []) if isinstance(data, dict) else []
    ideas: List[dict] = []
    for i, item in enumerate(raw_ideas):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        value_min = _int_or(item.get("value_min"), 10)
        value_max = _int_or(item.get("value_max"), value_min)
        ideas.append(
            {
                "id": _slugify(title) or f"idea-{i}",
                "title": title,
                "difficulty": str(item.get("difficulty", "Easy")).strip() or "Easy",
                "time_minutes": _int_or(item.get("time_minutes"), 20),
                "extra_materials": str(item.get("extra_materials", "Minimal materials")).strip()
                or "Minimal materials",
                "is_best_match": i == 0,
                "steps": [str(s).strip() for s in item.get("steps", []) if str(s).strip()],
                "value_min": value_min,
                "value_max": value_max,
                "usage_tags": [str(t).strip() for t in item.get("usage_tags", []) if str(t).strip()]
                or ["Personal use"],
            }
        )
    return ideas


def _int_or(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _fallback_ideas(label: str, material: str) -> List[dict]:
    """Provide safe local ideas when the model returns empty or malformed output."""
    text = f"{label} {material}".lower()
    if any(term in text for term in ("cloth", "clothing", "textile", "fabric", "garment")):
        templates = [
            ("Reusable Tote Bag", "Easy", 30, "Needle, thread, and handles", ["Wash and dry the clothing.", "Reinforce the seams and attach sturdy handles.", "Use the finished bag for groceries or daily items."]),
            ("Cushion Cover", "Easy", 25, "Cushion insert, needle, and thread", ["Wash and dry the fabric.", "Measure it around a cushion insert and stitch a close-fitting cover.", "Turn it inside out and use it as a washable cushion cover."]),
            ("Reusable Cleaning Cloths", "Easy", 15, "Scissors and a laundry bag", ["Wash the clothing before reuse.", "Cut it into practical cloth-sized pieces with clean edges.", "Store the cloths in a laundry bag and wash them after use."]),
        ]
    elif any(term in text for term in ("organic", "food", "fruit", "vegetable", "garden", "plant", "compost")):
        templates = [
            ("Home Compost Starter", "Easy", 20, "Compost bin, dry leaves, and soil", ["Remove plastic, glass, metal, meat, dairy, and oily material.", "Layer the remaining plant and food scraps with dry leaves.", "Turn the pile regularly and keep it damp, not wet."]),
            ("Leaf Mould", "Easy", 15, "Mesh bag or ventilated container", ["Collect clean, untreated leaves and remove litter.", "Pack the leaves loosely so air can circulate.", "Leave them to break down and use the finished leaf mould in soil."]),
            ("Garden Soil Amendment", "Medium", 30, "Mature compost and garden soil", ["Use only fully decomposed, safe compost.", "Mix a small amount into garden soil.", "Keep the soil covered and monitor plant growth."]),
        ]
    else:
        templates = [
            (f"Useful Reuse for {label}", "Easy", 20, "Basic household supplies", [f"Clean and dry the {material} item.", "Choose a simple use that does not alter or damage it.", "Test the finished reuse before putting it into regular service."]),
            (f"Organiser from {label}", "Easy", 25, "Labels and basic craft supplies", ["Clean the item and check that it is safe to handle.", "Add labels or a simple holder for small household items.", "Keep the organiser in a dry place and reuse it regularly."]),
            (f"Decorative Reuse of {label}", "Medium", 40, "Non-toxic paint or fabric", ["Clean the item thoroughly.", "Decorate it with safe, non-toxic materials.", "Use it as a display or storage piece instead of throwing it away."]),
        ]
    return [
        {
            "id": _slugify(title),
            "title": title,
            "difficulty": difficulty,
            "time_minutes": minutes,
            "extra_materials": extras,
            "is_best_match": i == 0,
            "steps": steps,
            "value_min": 20,
            "value_max": 150,
            "usage_tags": ["Personal use", "Reuse"],
        }
        for i, (title, difficulty, minutes, extras, steps) in enumerate(templates)
    ]


def _recovery_options(label: str, material: str) -> List[dict]:
    """Offer value-recovery routes without instructing users to open hazardous items."""
    item = label or material or "electronic item"
    templates = [
        ("Repair or Refurbishment Assessment", "Medium", 30, "Authorized service centre", [f"Back up your data and sign out of accounts on the {item}.", "Ask an authorized technician to assess repairability and battery safety.", "Repair and resell or donate it only if the technician confirms it is safe."]),
        ("Certified E-waste Buyback", "Easy", 15, "Data backup and proof of ownership", [f"Back up important data and perform a factory reset on the {item} if it powers on.", "Contact a certified e-waste recycler or manufacturer take-back program.", "Ask for a buyback receipt and keep the device out of household waste."]),
        ("Authorized Parts Recovery", "Easy", 20, "Certified e-waste recycler", ["Do not open, crush, puncture, burn, or remove the battery yourself.", "Take the item to a certified e-waste facility for safe parts recovery.", "Request confirmation that reusable components and materials were recovered responsibly."]),
    ]
    return [
        {
            "id": _slugify(title),
            "title": title,
            "difficulty": difficulty,
            "time_minutes": minutes,
            "extra_materials": extras,
            "is_best_match": i == 0,
            "steps": steps,
            "value_min": 50,
            "value_max": 2500,
            "usage_tags": ["Responsible recovery", "Sell"],
        }
        for i, (title, difficulty, minutes, extras, steps) in enumerate(templates)
    ]


async def generate_create_ideas(
    classification: AIClassification,
    db,
    force_refresh: bool = False,
) -> dict:
    """
    Return {"ideas": [...], "cached": bool} for the given classification.

    Ideas are cached per final_label to minimise model calls.
    """
    cache = await db["diy_ideas_cache"].find_one({"final_label": classification.label})

    is_special = classification.requires_special_handling or any(
        term in f"{classification.label} {classification.material}".lower()
        for term in SPECIAL_HANDLING_TERMS
    )
    # Hazardous items get safe recovery routes, never DIY instructions.
    if is_special:
        return {"ideas": _recovery_options(classification.label, classification.material), "cached": True}

    if cache and not force_refresh:
        return {"ideas": cache.get("ideas", []), "cached": True}

    prompt = SUGGESTION_PROMPT_TPL.format(
    label=classification.label,
    material=classification.material,
    category=classification.category,
    )
    # The image isn't strictly needed for idea generation; reuse label+material text.
    raw = await nim_client.call_vlm("", prompt)
    ideas = _parse_ideas(raw, classification.label, classification.material)
    if not ideas:
        ideas = _fallback_ideas(classification.label, classification.material)

    await db["diy_ideas_cache"].replace_one(
        {"final_label": classification.label},
        {"final_label": classification.label, "ideas": ideas, "material": classification.material},
        upsert=True,
    )

    return {"ideas": ideas, "cached": False}
