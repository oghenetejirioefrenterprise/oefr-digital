"""JSON schema validator with friendly error wrapping.

Validates data structures (distribution queue/log, launch reports, opportunity
briefs, product specs, etc.) against the JSON Schemas in ``state/_schemas/``.

``SchemaValidationError`` subclasses ``ValueError`` so existing call sites that
catch ``ValueError`` keep working while new code can catch the specific type.
"""
import json
from functools import lru_cache
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "state" / "_schemas"


class SchemaValidationError(ValueError):
    """Raised when JSON validation fails or the named schema is unknown."""


@lru_cache(maxsize=32)
def _load_schema(schema_name: str) -> dict:
    path = SCHEMAS_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        raise SchemaValidationError(f"No schema named '{schema_name}' at {path}")
    return json.loads(path.read_text())


def validate(schema_name: str, data: dict) -> None:
    """Validate *data* against the named schema.

    Raises ``SchemaValidationError`` if the data is invalid or the schema is
    unknown.
    """
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(data, schema, format_checker=jsonschema.FormatChecker())
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(
            f"{schema_name}: {e.message} (at {list(e.absolute_path)})"
        ) from e
