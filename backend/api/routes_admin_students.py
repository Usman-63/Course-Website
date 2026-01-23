"""
Admin student-operations routes backed by Google Sheets.
"""
from typing import Optional

from flask import Blueprint, jsonify, request

from core.auth import require_auth
from core.logger import logger
from students.student_helpers import (
    calculate_student_status,
    get_allowed_assignment_fields,
    get_student_email,
    get_total_labs_count,
    sort_students,
    validate_attendance_format,
    validate_grade_format,
)
from sheets.sheets_utils import validate_email_list
from firestore.operations_cache import (
    acquire_sync_lock,
    get_metrics_from_firestore,
    get_sync_status,
    release_sync_lock,
)


def register_admin_student_routes(
    api: Blueprint,
    sheets_manager: Optional[object],
) -> None:
    """Register admin student operations routes on the given blueprint."""

    @api.route("/admin/students/operations", methods=["GET"])
    @require_auth
    def get_all_students_operations():
        """Get all students with merged data from Survey, Register, and Firestore admin data."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Check force refresh
            force_refresh = request.args.get("force_refresh", "false").lower() == "true"
            students, _metrics = sheets_manager.get_all_students(
                use_firestore_cache=True,
                force_refresh=force_refresh,
            )

            # Get sort parameters from query string
            sort_by = request.args.get("sort_by", "name")  # Default: sort by name
            sort_order = request.args.get("sort_order", "asc")  # Default: ascending

            # Sort students
            sort_students(students, sort_by=sort_by, sort_order=sort_order)

            logger.info(
                f"Retrieved {len(students)} students for operations (sorted by {sort_by}, {sort_order})"
            )
            return jsonify({"success": True, "students": students}), 200
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error getting students: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error getting all students operations: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed to fetch students: {str(e)}"}), 500

    @api.route("/admin/students/operations/<email>", methods=["GET"])
    @require_auth
    def get_student_operations(email):
        """Get specific student data by email."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            if not email or not email.strip():
                return jsonify({"error": "Email address is required"}), 400

            student = sheets_manager.get_student_by_email(email)
            if not student:
                logger.info(f"Student not found: {email}")
                return jsonify({"error": "Student not found"}), 404

            return jsonify({"success": True, "student": student}), 200
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error getting student: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error getting student operations: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch student: {str(e)}"}), 500

    @api.route("/admin/students/operations/<email>", methods=["PUT"])
    @require_auth
    def update_student_operations(email):
        """Update student admin data in Firestore (attendance, grades, evaluation)."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            if not email or not email.strip():
                return jsonify({"error": "Email address is required"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400

            # Get total labs to determine allowed assignment grade fields
            total_labs = get_total_labs_count()
            allowed_fields = get_allowed_assignment_fields(total_labs)

            updates = {k: v for k, v in data.items() if k in allowed_fields}

            if not updates:
                return (
                    jsonify(
                        {
                            "error": "No valid fields to update. Allowed fields: "
                            + ", ".join(allowed_fields)
                        }
                    ),
                    400,
                )

            # Validate attendance format if provided
            if "Attendance" in updates:
                is_valid, error_msg = validate_attendance_format(updates["Attendance"])
                if not is_valid:
                    return jsonify({"error": error_msg}), 400

            # Validate grade fields are strings or numbers
            for grade_field in allowed_fields:
                if grade_field.startswith("Assignment") and grade_field in updates:
                    is_valid, error_msg = validate_grade_format(updates[grade_field])
                    if not is_valid:
                        return jsonify(
                            {"error": f"{grade_field} {error_msg}"}
                        ), 400

            success = sheets_manager.update_student_data(email, updates)
            if success:
                logger.info(f"Updated student operations for: {email}")
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Student data updated successfully",
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"error": "Failed to update student data"}), 500
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error updating student: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error updating student operations: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to update student: {str(e)}"}), 500

    @api.route("/admin/students/operations/bulk", methods=["POST"])
    @require_auth
    def bulk_update_students_operations():
        """Bulk update multiple students in Firestore admin data."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            data = request.get_json()
            if not data or "updates" not in data:
                return (
                    jsonify({"error": 'Request body must contain "updates" array'}),
                    400,
                )

            updates = data["updates"]
            if not isinstance(updates, list):
                return jsonify({"error": '"updates" must be an array'}), 400

            if len(updates) == 0:
                return jsonify({"error": "Updates array cannot be empty"}), 400

            if len(updates) > 100:
                return jsonify({"error": "Cannot update more than 100 students at once"}), 400

            # Get total labs to determine allowed assignment grade fields
            total_labs = get_total_labs_count()
            allowed_fields = get_allowed_assignment_fields(total_labs)

            # Validate each update has email and valid fields
            for i, update in enumerate(updates):
                if not isinstance(update, dict):
                    return (
                        jsonify(
                            {"error": f"Update at index {i} must be an object"}
                        ),
                        400,
                    )
                if "email" not in update:
                    return (
                        jsonify(
                            {
                                "error": f'Update at index {i} must have an "email" field'
                            }
                        ),
                        400,
                    )
                if not update["email"] or not str(update["email"]).strip():
                    return (
                        jsonify(
                            {"error": f"Update at index {i} has invalid email"}
                        ),
                        400,
                    )
                # Check for invalid fields
                invalid_fields = [
                    k for k in update.keys() if k != "email" and k not in allowed_fields
                ]
                if invalid_fields:
                    return (
                        jsonify(
                            {
                                "error": f'Update at index {i} has invalid fields: {", ".join(invalid_fields)}'
                            }
                        ),
                        400,
                    )

            result = sheets_manager.bulk_update_admin_logs(updates)
            # Handle both old boolean return and new dict return for backward compatibility
            if isinstance(result, dict):
                success = result.get('success', False)
                updated_count = result.get('updated', 0)
                failed_count = result.get('failed', 0)
                skipped_count = result.get('skipped', 0)
            else:
                success = result
                updated_count = len(updates) if success else 0
                failed_count = 0
                skipped_count = 0
            
            if success:
                logger.info(
                    f"Bulk updated {updated_count} students "
                    f"({failed_count} failed, {skipped_count} skipped)"
                )
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": f"Updated {updated_count} students successfully",
                            "stats": {
                                "updated": updated_count,
                                "failed": failed_count,
                                "skipped": skipped_count,
                            },
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Some updates failed: {updated_count} updated, {failed_count} failed, {skipped_count} skipped",
                            "stats": {
                                "updated": updated_count,
                                "failed": failed_count,
                                "skipped": skipped_count,
                            },
                        }
                    ),
                    500,
                )
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error in bulk update: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to bulk update: {str(e)}"}), 500

    @api.route("/admin/students/operations/metrics", methods=["GET"])
    @require_auth
    def get_students_operations_metrics():
        """Get dashboard metrics: total students, paid count, onboarding percentage."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Prefer cached metrics when available
            metrics = get_metrics_from_firestore() or {}
            if not metrics:
                # Fallback: recompute from Sheets
                _students, metrics = sheets_manager.get_all_students(
                    use_firestore_cache=True,
                    force_refresh=False,
                )
            return jsonify({"success": True, "metrics": metrics}), 200
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch metrics: {str(e)}"}), 500

    @api.route("/admin/students/operations/status", methods=["GET"])
    @require_auth
    def get_students_operations_status():
        """Get students with missing items (payment, resume, attendance, grades)."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            students, _metrics = sheets_manager.get_all_students(
                use_firestore_cache=True,
                force_refresh=False,
            )
            total_labs = get_total_labs_count()
            status = calculate_student_status(students, total_labs)

            return jsonify({"success": True, "status": status}), 200
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error getting status: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch status: {str(e)}"}), 500

    @api.route("/admin/students/operations/sync", methods=["POST"])
    @require_auth
    def sync_students_operations():
        """
        Trigger a manual sync from Google Sheets to Firestore cache.

        This endpoint is idempotent and uses a sync lock to avoid concurrent syncs.
        """
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Attempt to acquire sync lock
            lock_acquired = False
            try:
                if not acquire_sync_lock():
                    status = get_sync_status()
                    logger.info("Sync already in progress, rejecting new sync request")
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Sync already in progress",
                                "status": status,
                            }
                        ),
                        429,
                    )
                lock_acquired = True

                # Force-refresh from Sheets and push to Firestore via manager
                students, metrics = sheets_manager.get_all_students(
                    use_firestore_cache=True,
                    force_refresh=True,
                )
                release_sync_lock(success=True)
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Sync completed successfully",
                            "student_count": len(students),
                            "metrics": metrics,
                        }
                    ),
                    200,
                )
            except Exception as sync_err:
                logger.error(f"Error during manual sync: {sync_err}", exc_info=True)
                if lock_acquired:
                    release_sync_lock(success=False, error=str(sync_err))
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Sync failed",
                            "error": str(sync_err),
                        }
                    ),
                    500,
                )
            finally:
                # Ensure lock is always released, even if an unexpected error occurs
                if lock_acquired:
                    try:
                        # Double-check lock status and release if still held
                        status = get_sync_status()
                        if status.get('status') == 'IN_PROGRESS':
                            release_sync_lock(success=False, error="Unexpected error during sync")
                    except Exception as release_err:
                        logger.error(f"Error releasing sync lock in finally: {release_err}", exc_info=True)

        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error handling sync request: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to start sync: {str(e)}"}), 500

    @api.route("/admin/students/operations/sync-status", methods=["GET"])
    @require_auth
    def get_students_operations_sync_status():
        """
        Get Firestore sync status and latest metrics snapshot.
        """
        try:
            status = get_sync_status()
            metrics = get_metrics_from_firestore() or {}

            return (
                jsonify(
                    {
                        "success": True,
                        "status": status,
                        "metrics": metrics,
                    }
                ),
                200,
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error getting sync status: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch sync status: {str(e)}"}), 500

    @api.route("/admin/students/operations/all", methods=["GET"])
    @require_auth
    def get_all_students_operations_combined():
        """Get all students data, metrics, and status in a single call."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Check force refresh
            force_refresh = (
                request.args.get("force_refresh", "false").lower() == "true"
            )

            # Call get_all_students() ONCE
            students, metrics = sheets_manager.get_all_students(
                use_firestore_cache=True,
                force_refresh=force_refresh,
            )

            # Get sort parameters from query string
            sort_by = request.args.get("sort_by", "name")
            sort_order = request.args.get("sort_order", "asc")

            # Sort students
            sort_students(students, sort_by=sort_by, sort_order=sort_order)

            # Calculate status from the same data (metrics already computed)
            total_labs = get_total_labs_count()
            status = calculate_student_status(students, total_labs)

            logger.info(
                f"Retrieved combined operations data for {len(students)} students (sorted by {sort_by}, {sort_order})"
            )
            return (
                jsonify(
                    {
                        "success": True,
                        "students": students,
                        "metrics": metrics,
                        "status": status,
                    }
                ),
                200,
            )

        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error getting combined operations data: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

    @api.route("/admin/students/operations/emails", methods=["GET"])
    @require_auth
    def get_students_operations_emails():
        """Export all student emails as comma-separated list."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            students, _metrics = sheets_manager.get_all_students(
                use_firestore_cache=True,
                force_refresh=False,
            )

            emails = []
            for student in students:
                email = get_student_email(student)
                if email:
                    emails.append(email)

            # Validate and format emails
            valid_emails = validate_email_list(emails)

            # Return as comma-separated string and as array
            emails_string = ", ".join(valid_emails)

            return (
                jsonify(
                    {
                        "success": True,
                        "emails": valid_emails,
                        "emails_string": emails_string,
                        "count": len(valid_emails),
                    }
                ),
                200,
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error exporting emails: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to export emails: {str(e)}"}), 500


