"""Shared Pydantic helpers used across models."""

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class PyObjectId(str):
    """Pydantic-compatible string wrapper for MongoDB ObjectIds."""

    @classmethod
    def _validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError(f"Invalid ObjectId: {v!r}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.to_string_ser_schema(),
        )


def coerce_object_ids(doc: dict) -> dict:
    """Convert ObjectId fields in a Mongo document to their string form for JSON output."""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, dict) and "_id" in value:
            # nested scan->_id style references
            value["_id"] = str(value["_id"])
    return doc