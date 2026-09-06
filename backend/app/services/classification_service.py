"""Waste classification service: prompt the NIM VLM and parse a structured result.

The model is asked to return strict JSON. We also apply a deterministic keyword
safety net so dangerous items (batteries, e-waste, chemicals, sharps, bulbs) are
always flagged for special handling even if the model misses them.
"""

import json
import re

from app.models.waste_scan import AIClassification, CATEGORY_VALUES
from app.services import nim_client
from app.utils.image_utils import to_data_uri

HAZARD_KEYWORDS = [
    "battery",
    "lithium",
    "e-waste",
    "electronic",
    "phone",
    "mobile",
    "smartphone",
    "cellphone",
    "cell phone",
    "circuit",
    "paint",
    "chemical",
    "solvent",
    "pesticide",
    "insecticide",
    "medication",
    "medicine",
    "pill",
    "syringe",
    "needle",
    "sharps",
    "cfl",
    "fluorescent",
    "led bulb",
    "mercury",
    "thermometer",
    "aerosol",
    "gas cylinder",
    "propane",
    "oil",
    "acid",
    "corrosive",
    "bleach",
    "cleaner",
    "cosmetic",
    "nail polish",
    "mask",
    "glove",
    "sanitizer",
    "cigarette",
]

FIRST_CHAR_RE = re.compile(r"[\[\{\"]")
MARKDOWN_FIELD_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\*{0,2}\s*"
    r"(Label|Material|Category|Condition|Requires Special Handling|Confidence)"
    r"\s*\*{0,2}\s*:\s*(.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_markdown_fields(text: str) -> dict:
    """Convert common VLM Markdown key/value output into classification fields."""
    fields = {}
    key_map = {
        "label": "label",
        "material": "material",
        "category": "category",
        "condition": "condition",
        "requires special handling": "requires_special_handling",
        "confidence": "confidence",
    }
    for match in MARKDOWN_FIELD_RE.finditer(text):
        key = key_map[match.group(1).lower()]
        value = re.sub(r"\*{1,2}|`", "", match.group(2)).strip()
        fields[key] = value
    if len(fields) >= 3 and "label" in fields and "category" in fields:
        return fields
    return {}


def _extract_prose_classification(text: str) -> dict:
    """Create a conservative result from a model's plain-language description."""
    lowered = text.lower()
    visible_materials = []
    for material, terms in (
        ("plastic", ("plastic", "polymer")),
        ("metal", ("metal", "iron", "steel", "aluminium", "aluminum")),
        ("glass", ("glass",)),
        ("paper/cardboard", ("paper", "cardboard")),
        ("food and plant matter", ("food", "plant", "vegetable", "fruit", "leaf")),
        ("wood", ("wood", "wooden", "timber")),
        ("fabric/textile", ("fabric", "textile", "cloth", "cotton")),
    ):
        if any(term in lowered for term in terms):
            visible_materials.append(material)
    # VLMs sometimes explain the object instead of following JSON mode. Recover
    # an explicit label when possible rather than returning a 502 to the user.
    label_match = re.search(r"(?:label|item|object)\s*(?:is|:|was)\s*[\"']?([A-Za-z][A-Za-z0-9 /&-]{1,80})", text, re.IGNORECASE)
    explicit_label = label_match.group(1).strip(" .,:;\"'") if label_match else ""
    if not visible_materials and not explicit_label:
        return {}

    if not visible_materials:
        if re.search(r"furniture|dresser|nightstand|table|chair|wood", lowered):
            visible_materials.append("wood")
        else:
            visible_materials.append("unknown material")

    if explicit_label:
        label = explicit_label.title()
    elif "wood" in visible_materials and any(term in lowered for term in ("nightstand", "dresser", "table", "chair", "shelf", "cabinet")):
        label = next(term.title() for term in ("nightstand", "dresser", "table", "chair", "shelf", "cabinet") if term in lowered)
    else:
        label = f"{visible_materials[0].title()} Waste"

    is_mixed = len(visible_materials) > 1 or any(term in lowered for term in ("pile", "mixed", "various", "scattered"))
    if is_mixed:
        return {
            "label": "Mixed Waste",
            "material": ", ".join(visible_materials),
            "category": "General Waste",
            "condition": "Mixed materials; separate before recovery",
            "requires_special_handling": _keyword_hazard(lowered),
            "confidence": 0.55,
        }
    return {
        "label": label,
        "material": visible_materials[0],
        "category": "Organic/Compostable" if visible_materials[0] == "food and plant matter" else ("Reusable" if any(term in lowered for term in ("furniture", "nightstand", "dresser", "table", "chair", "usable", "intact")) else "Recyclable"),
        "condition": "Visibly intact; assess before reuse" if any(term in lowered for term in ("furniture", "nightstand", "dresser", "table", "chair")) else "Check for contamination before handling",
        "requires_special_handling": _keyword_hazard(lowered),
        "confidence": 0.45 if explicit_label else 0.35,
    }


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from the model response."""
    stripped = text.strip()
    # Model sometimes wraps JSON in ```json fences.
    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    # Fall back to locating the first { or [ and consuming the last } or ].
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        markdown_fields = _extract_markdown_fields(stripped)
        if markdown_fields:
            return markdown_fields
        prose_fields = _extract_prose_classification(stripped)
        if prose_fields:
            return prose_fields
        start = FIRST_CHAR_RE.search(stripped)
        if not start:
            raise ValueError("No JSON found in model output")
        end_marker = "]" if stripped[start.start()] == "[" else "}"
        end = stripped.rfind(end_marker)
        if end == -1:
            raise ValueError("Unbalanced JSON in model output")
        return json.loads(stripped[start.start() : end + 1])


def _safe_text(value, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return default


def _safe_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"true", "yes", "y", "1", "hazardous"}
    return default


def _safe_number(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _keyword_hazard(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in HAZARD_KEYWORDS)


def _normalise_category(category: str, label: str, material: str) -> str:
    """Map common model wording to the categories exposed by the API."""
    text = " ".join((category, label, material)).lower()
    if _keyword_hazard(text):
        return "Hazardous/Special"
    if any(term in text for term in ("organic", "food scrap", "fruit peel", "vegetable", "garden waste", "plant matter", "compost")):
        return "Organic/Compostable"
    if category in CATEGORY_VALUES:
        return category
    if any(term in text for term in ("reus", "upcycl")):
        return "Reusable"
    if any(term in text for term in ("recycl", "plastic", "glass", "paper", "cardboard", "aluminium", "aluminum", "metal")):
        return "Recyclable"
    return category if category in CATEGORY_VALUES else "General Waste"


CLASSIFICATION_PROMPT = """You are WasteWise, a visual waste-classification system.

Analyze the image itself. First identify every clearly visible waste type, then decide
which type is dominant. Never use a default label and never infer an object that is not
visibly present. If there are several substantial waste types, use a mixed-waste label
and summarize the composition. If the image is unclear, use "Unknown waste item" and
lower the confidence instead of guessing.

Classification rules:
- Food scraps, fruit or vegetable peels, flowers, leaves, and untreated plant matter are Organic/Compostable.
- Paper, cardboard, glass, metal, and clean accepted plastics are Recyclable when visibly suitable for recycling.
- An intact clean object that can be used again is Reusable.
- Batteries, electronics, chemicals, medicines, sharps, bulbs, aerosols, gas containers, oils, and contaminated hazardous items are Hazardous/Special.
- Contaminated, inseparable, or non-recoverable material is General Waste.
- Set requires_special_handling to true only for hazardous or potentially hazardous material.

Return ONLY one valid JSON object. Do not return markdown, explanations, multiple objects,
or a JSON array. Use exactly these keys and values:
{
  "label": "A short name based only on visible contents",
  "material": "The dominant material or a concise description of the visible composition",
  "category": "Recyclable | Reusable | Organic/Compostable | Hazardous/Special | General Waste",
  "condition": "A short visual condition or contamination assessment",
  "requires_special_handling": true,
  "confidence": 0.0
}

The confidence must be a number from 0.0 to 1.0. Make the label specific when the image
supports it and broad when it does not. Base the answer on the image, not on these rules' examples.
"""


async def classify_waste(abs_path: str) -> AIClassification:
    """Run classification against the NIM VLM and return a validated result."""
    data_uri = to_data_uri(abs_path)
    try:
        raw = await nim_client.call_vlm(data_uri, CLASSIFICATION_PROMPT, max_tokens=512)
    except nim_client.NimError as exc:
        # Surface a clear message; operator should configure the API key.
        raise nim_client.NimError(f"Waste classification unavailable: {exc}")

    try:
        parsed = _extract_json(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        preview = (raw or "").strip()[:300]
        raise nim_client.NimError(
            "NIM returned a response that was not valid classification JSON. "
            f"Response preview: {preview!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise nim_client.NimError("NIM returned JSON, but it was not a classification object")

    label = _safe_text(parsed.get("label"), "Unknown item")
    material = _safe_text(parsed.get("material"), "Unknown")
    category = _normalise_category(
        _safe_text(parsed.get("category"), "General Waste"), label, material
    )

    condition = _safe_text(parsed.get("condition"), "Check item for safe handling")
    requires_special_handling = _safe_bool(parsed.get("requires_special_handling")) or (
        _keyword_hazard(label) or _keyword_hazard(material) or _keyword_hazard(category)
    )
    confidence = min(1.0, max(0.0, _safe_number(parsed.get("confidence"), 0.0)))

    if requires_special_handling and category != "Hazardous/Special":
        category = "Hazardous/Special"

    return AIClassification(
        label=label,
        material=material,
        category=category,
        condition=condition,
        requires_special_handling=requires_special_handling,
        confidence=confidence,
        raw_model_text=raw,
    )
