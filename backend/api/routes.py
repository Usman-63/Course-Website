from flask import Blueprint

from api.routes_admin_core import register_admin_core_routes
from api.routes_admin_students import register_admin_student_routes
from api.routes_classes import register_class_routes
from api.routes_public import register_public_routes
from core.logger import logger

import time


api = Blueprint("api", __name__)


def normalize_course_data(data):
    """Ensure data follows the new multi-course structure."""
    if "courses" in data and isinstance(data["courses"], list):
        return data

    # Create default course from existing data
    default_course = {
        "id": "default-course",
        "title": "Main Course",
        "isVisible": True,
        "modules": data.get("modules", []),
        "links": data.get("links", []),
        "metadata": data.get(
            "metadata",
            {
                "schedule": "",
                "pricing": {"standard": 0, "student": 0},
            },
        ),
    }

    return {
        "version": data.get("version", int(time.time() * 1000)),
        "courses": [default_course],
    }


# Initialize Google Sheets manager
try:
    from sheets.google_sheets_manager import GoogleSheetsManager

    sheets_manager = GoogleSheetsManager()
except Exception as e:  # pragma: no cover - defensive
    logger.warning(f"Google Sheets manager not initialized: {type(e).__name__}")
    sheets_manager = None


# Register route groups on the shared blueprint
register_public_routes(api, normalize_course_data)
register_admin_core_routes(api, normalize_course_data, sheets_manager)
register_admin_student_routes(api, sheets_manager)
register_class_routes(api, sheets_manager)

