"""Keeps the frontend and backend maintenance category lists in sync.

Run from backend/: pytest -q
"""

import re
from pathlib import Path

from app.schemas import SERVICE_TYPES

FRONTEND_LIST = Path(__file__).resolve().parents[2] / "frontend" / "src" / "serviceTypes.js"


def test_frontend_service_types_match_backend():
    source = FRONTEND_LIST.read_text(encoding="utf-8")
    frontend_types = set(re.findall(r"'([^']+)'", source.split("export const SERVICE_TYPES")[1]))

    assert frontend_types == set(SERVICE_TYPES)
