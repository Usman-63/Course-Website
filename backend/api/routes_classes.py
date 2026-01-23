"""
Class management routes (Classes sheet + attendance).
"""
from typing import Optional

from flask import Blueprint, jsonify, request

from core.auth import require_auth
from core.logger import logger


def register_class_routes(
    api: Blueprint,
    sheets_manager: Optional[object],
) -> None:
    """Register class management routes on the given blueprint."""

    @api.route("/admin/classes", methods=["GET"])
    @require_auth
    def get_classes():
        """Get all classes."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            classes = sheets_manager.read_classes()
            return jsonify({"success": True, "classes": classes}), 200
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error getting classes: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/classes", methods=["POST"])
    @require_auth
    def add_class():
        """Add a new class."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing request body"}), 400

            # Generate ID if missing
            if "id" not in data:
                import uuid

                data["id"] = str(uuid.uuid4())

            success = sheets_manager.add_class(data)
            if success:
                return jsonify({"success": True, "class": data}), 201
            else:
                return jsonify({"error": "Failed to add class"}), 500
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error adding class: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/classes/<class_id>", methods=["DELETE"])
    @require_auth
    def delete_class(class_id):
        """Delete a class."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            success = sheets_manager.delete_class(class_id)
            if success:
                return jsonify({"success": True}), 200
            else:
                return (
                    jsonify(
                        {"error": "Class not found or failed to delete"}
                    ),
                    404,
                )
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error deleting class: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/classes/<class_id>/attendance", methods=["POST"])
    @require_auth
    def mark_class_attendance(class_id):
        """
        Mark attendance for a class (bulk update).
        
        Uses locking to prevent duplicate concurrent requests and idempotency
        to skip unnecessary updates.
        """
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            data = request.get_json() or {}
            present_emails = data.get("present_emails", [])
            
            if not isinstance(present_emails, list):
                logger.error(f"Invalid present_emails format: {type(present_emails)}")
                return jsonify({"error": "present_emails must be a list"}), 400

            # Validate emails are strings
            present_emails = [str(email).strip() for email in present_emails if email]
            
            logger.info(f"Marking attendance for class {class_id} with {len(present_emails)} present students")
            
            # Returns dict with status, success, updated, skipped, etc.
            result = sheets_manager.bulk_mark_attendance(class_id, present_emails)
            
            # Handle different status types
            status = result.get('status', 'unknown')
            
            if status == 'duplicate_request':
                # Another request is already processing
                logger.warning(f"Attendance marking for class {class_id} rejected (duplicate concurrent request)")
                return jsonify({
                    "error": "Attendance marking already in progress for this class",
                    "code": "DUPLICATE_REQUEST"
                }), 429
            
            elif status == 'no_changes':
                # All attendance already set correctly
                logger.info(f"Attendance for class {class_id} already set correctly, no updates needed")
                return jsonify({
                    "success": True,
                    "message": result.get('message', 'No changes needed'),
                    "stats": {
                        "updated": result.get('updated', 0),
                        "skipped": result.get('skipped', 0)
                    }
                }), 200
            
            elif status == 'completed':
                # Successfully updated
                logger.info(f"Successfully marked attendance for class {class_id}")
                return jsonify({
                    "success": True,
                    "message": result.get('message', 'Attendance marked successfully'),
                    "stats": {
                        "updated": result.get('updated', 0),
                        "skipped": result.get('skipped', 0),
                        "failed": result.get('failed', 0)
                    }
                }), 200
            
            else:
                # Failed
                logger.error(f"Failed to mark attendance for class {class_id}: {result.get('message', 'Unknown error')}")
                return jsonify({
                    "error": result.get('message', 'Failed to mark attendance'),
                    "stats": {
                        "updated": result.get('updated', 0),
                        "skipped": result.get('skipped', 0),
                        "failed": result.get('failed', 0)
                    }
                }), 500
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error marking attendance for class {class_id}: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500


