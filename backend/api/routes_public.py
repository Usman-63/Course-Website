"""
Public (unauthenticated) API routes.
"""
import hashlib
import json
from typing import Callable, Optional

from flask import Blueprint, jsonify, request

from firestore.course_data import get_course_data as get_course_data_from_firestore
from core.logger import logger


def register_public_routes(
    api: Blueprint,
    normalize_course_data: Callable[[dict], dict],
) -> None:
    """Register public course/notification routes on the given blueprint."""

    @api.route("/notification", methods=["POST"])
    def notification():
        """Handle notification signup."""
        try:
            data = request.get_json()
            email = data.get("email") if data else None

            if not email:
                return jsonify({"error": "Email is required"}), 400

            # In a real app, we would save this to a database or send an email
            logger.info(f"Notification request for email: {email}")

            return jsonify({"success": True, "message": "We will notify you"}), 200
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/course/data", methods=["GET"])
    def get_course_data():
        """
        Get all course data (public).

        Returns primary visible course for backward compatibility.
        Reads from Firestore.
        """
        try:
            # Get data from Firestore
            data = get_course_data_from_firestore()
            
            # If no data, return empty structure
            if not data:
                return (
                    jsonify(
                        {
                            "modules": [],
                            "metadata": {
                                "schedule": "",
                                "pricing": {"standard": 0, "student": 0},
                            },
                        }
                    ),
                    200,
                )

            normalized = normalize_course_data(data)

            # Find primary visible course (first one that is visible)
            primary_course = None
            if normalized.get("courses"):
                for course in normalized["courses"]:
                    if course.get("isVisible", True):
                        primary_course = course
                        break

                # If no visible course found, fallback to first one (or empty)
                if not primary_course and normalized["courses"]:
                    primary_course = normalized["courses"][0]

            if primary_course:
                # Return flattened structure for frontend compatibility
                return (
                    jsonify(
                        {
                            "version": normalized.get("version", 0),
                            "modules": primary_course.get("modules", []),
                            "links": primary_course.get("links", []),
                            "metadata": primary_course.get("metadata", {}),
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"modules": [], "metadata": {}}), 200

        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/course/version", methods=["GET"])
    def get_course_version():
        """Get course data version (public)."""
        try:
            # Get data from Firestore
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"version": 0}), 200

            version = data.get("version")

            # If no explicit version exists, generate a stable hash from the data
            if not version:
                try:
                    # Create a copy to avoid modifying original
                    data_copy = data.copy()
                    # Remove version key if it exists (though it shouldn't if we are here)
                    data_copy.pop("version", None)
                    # Generate stable string representation
                    data_str = json.dumps(data_copy, sort_keys=True)
                    # Create numeric hash (use first 13 digits to simulate timestamp length)
                    version = int(
                        hashlib.sha256(data_str.encode("utf-8")).hexdigest(), 16
                    ) % (10**13)
                except Exception:  # pragma: no cover - defensive
                    version = 0

            return jsonify({"version": version}), 200
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500


