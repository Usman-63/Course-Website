"""
Admin student-operations routes backed by Google Sheets.
"""
from typing import Optional
import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from core.auth import require_auth
from core.logger import logger
from students.student_helpers import (
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
from firestore.admin_data import (
    get_all_users_admin_data,
    get_user_admin_data,
    get_user_admin_data_by_email,
    update_user_admin_data,
    update_user_admin_data_by_email,
    bulk_update_users_admin_data,
)


def register_admin_student_routes(
    api: Blueprint,
    sheets_manager: Optional[object],
) -> None:
    """Register admin student operations routes on the given blueprint."""

    @api.route("/admin/students", methods=["GET"])
    @require_auth
    def get_all_students():
        """Get all Firebase users with their admin data."""
        try:
            users = get_all_users_admin_data()
            
            # Convert to format expected by frontend
            students = []
            for user in users:
                student = {
                    'Email Address': user.get('email', ''),
                    'Name': user.get('name', ''),
                    'attendance': user.get('attendance', {}),
                    'assignmentGrades': user.get('assignmentGrades', {}),
                    'Teacher Evaluation': user.get('teacherEvaluation', ''),
                    'Payment Status': user.get('paymentStatus', ''),
                    'Payment Comment': user.get('paymentComment', ''),
                    'paymentScreenshot': user.get('paymentScreenshot', ''),
                    'Resume Link': user.get('resumeLink', ''),
                    '_id': user.get('_id', ''),  # UID
                    'isActive': user.get('isActive'),  # Include isActive field
                    'role': user.get('role'),  # Include role field
                }
                students.append(student)
            
            logger.info(f"Retrieved {len(students)} users with admin data")
            return jsonify({"success": True, "students": students}), 200
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500

    @api.route("/admin/students/<uid>", methods=["GET"])
    @require_auth
    def get_student_by_uid(uid):
        """Get single Firebase user with admin data by UID."""
        try:
            user = get_user_admin_data(uid)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            student = {
                'Email Address': user.get('email', ''),
                'Name': user.get('name', ''),
                'attendance': user.get('attendance', {}),
                'assignmentGrades': user.get('assignmentGrades', {}),
                'Teacher Evaluation': user.get('teacherEvaluation', ''),
                'Payment Status': user.get('paymentStatus', ''),
                'Payment Comment': user.get('paymentComment', ''),
                'paymentScreenshot': user.get('paymentScreenshot', ''),
                'Resume Link': user.get('resumeLink', ''),
                '_id': user.get('_id', ''),  # UID
            }
            
            return jsonify({"success": True, "student": student}), 200
        except Exception as e:
            logger.error(f"Error getting user {uid}: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to fetch user: {str(e)}"}), 500

    @api.route("/admin/students/<uid>", methods=["PUT"])
    @require_auth
    def update_student_by_uid(uid):
        """Update user admin data by UID."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400

            # Get total labs to determine allowed assignment grade fields
            total_labs = get_total_labs_count()
            allowed_fields = get_allowed_assignment_fields(total_labs)

            updates = {k: v for k, v in data.items() if k in allowed_fields or k in ['attendance', 'assignmentGrades', 'teacherEvaluation', 'paymentStatus', 'paymentComment', 'paymentScreenshot', 'resumeLink', 'name']}

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
            if "Attendance" in updates or "attendance" in updates:
                attendance = updates.get("Attendance") or updates.get("attendance")
                is_valid, error_msg = validate_attendance_format(attendance)
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

            success = update_user_admin_data(uid, updates)
            if success:
                logger.info(f"Updated user admin data for: {uid}")
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "User data updated successfully",
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"error": "Failed to update user data"}), 500
        except ValueError as e:
            logger.warning(f"Validation error updating user: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

    @api.route("/admin/students/register", methods=["GET"])
    @require_auth
    def get_register_students():
        """Get Register form data only (no merging)."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Check force refresh
            force_refresh = request.args.get("force_refresh", "false").lower() == "true"
            students = sheets_manager.get_register_students(force_refresh=force_refresh)

            # Get sort parameters from query string
            sort_by = request.args.get("sort_by", "name")  # Default: sort by name
            sort_order = request.args.get("sort_order", "asc")  # Default: ascending

            # Sort students
            sort_students(students, sort_by=sort_by, sort_order=sort_order)

            logger.info(
                f"Retrieved {len(students)} Register form entries (sorted by {sort_by}, {sort_order})"
            )
            return jsonify({"success": True, "students": students}), 200
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error getting Register students: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error getting Register students: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed to fetch Register students: {str(e)}"}), 500

    @api.route("/admin/students/survey", methods=["GET"])
    @require_auth
    def get_survey_students():
        """Get Survey form data only (no merging)."""
        try:
            if not sheets_manager:
                logger.error("Google Sheets manager not configured")
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Check force refresh
            force_refresh = request.args.get("force_refresh", "false").lower() == "true"
            students = sheets_manager.get_survey_students(force_refresh=force_refresh)

            # Get sort parameters from query string
            sort_by = request.args.get("sort_by", "name")  # Default: sort by name
            sort_order = request.args.get("sort_order", "asc")  # Default: ascending

            # Sort students
            sort_students(students, sort_by=sort_by, sort_order=sort_order)

            logger.info(
                f"Retrieved {len(students)} Survey form entries (sorted by {sort_by}, {sort_order})"
            )
            return jsonify({"success": True, "students": students}), 200
        except ValueError as e:  # pragma: no cover - defensive
            logger.warning(f"Validation error getting Survey students: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error getting Survey students: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed to fetch Survey students: {str(e)}"}), 500

    @api.route("/admin/students/operations", methods=["GET"])
    @require_auth
    def get_all_students_operations():
        """DEPRECATED: Get all students with merged data. Use /admin/students/register or /admin/students/survey instead."""
        try:
            logger.warning("DEPRECATED: /admin/students/operations endpoint is deprecated. Use /admin/students/register or /admin/students/survey instead.")
            return jsonify({"error": "This endpoint is deprecated. Use /admin/students/register or /admin/students/survey instead."}), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error in deprecated endpoint: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed: {str(e)}"}), 500

    @api.route("/admin/students/operations/<email>", methods=["GET"])
    @require_auth
    def get_student_operations(email):
        """DEPRECATED: Get specific student data by email. Use /admin/students/register or /admin/students/survey with search instead."""
        try:
            logger.warning("DEPRECATED: /admin/students/operations/<email> endpoint is deprecated.")
            return jsonify({"error": "This endpoint is deprecated. Use /admin/students/register or /admin/students/survey instead."}), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error in deprecated endpoint: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed: {str(e)}"}), 500

    @api.route("/admin/students/operations/<email>", methods=["PUT"])
    @require_auth
    def update_student_operations(email):
        """Update student admin data in Firestore (attendance, grades, evaluation) by email."""
        try:
            if not email or not email.strip():
                return jsonify({"error": "Email address is required"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body is required"}), 400

            # Get total labs to determine allowed assignment grade fields
            total_labs = get_total_labs_count()
            allowed_fields = get_allowed_assignment_fields(total_labs)

            updates = {k: v for k, v in data.items() if k in allowed_fields or k in ['attendance', 'assignmentGrades', 'teacherEvaluation', 'paymentStatus', 'paymentComment', 'paymentScreenshot', 'resumeLink', 'name']}

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
            if "Attendance" in updates or "attendance" in updates:
                attendance = updates.get("Attendance") or updates.get("attendance")
                is_valid, error_msg = validate_attendance_format(attendance)
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

            # Update via Firestore (will find user by email)
            success = update_user_admin_data_by_email(email, updates)
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

            result = bulk_update_users_admin_data(updates)
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
        """DEPRECATED: Get dashboard metrics. Metrics are no longer calculated for Operations tab."""
        try:
            logger.warning("DEPRECATED: /admin/students/operations/metrics endpoint is deprecated.")
            return jsonify({"error": "This endpoint is deprecated. Operations tab no longer shows metrics."}), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error in deprecated endpoint: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed: {str(e)}"}), 500

    @api.route("/admin/students/operations/status", methods=["GET"])
    @require_auth
    def get_students_operations_status():
        """DEPRECATED: Get students with missing items. Status is no longer calculated for Operations tab."""
        try:
            logger.warning("DEPRECATED: /admin/students/operations/status endpoint is deprecated.")
            return jsonify({"error": "This endpoint is deprecated. Operations tab no longer shows status."}), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error in deprecated endpoint: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed: {str(e)}"}), 500

    @api.route("/admin/students/operations/sync", methods=["POST"])
    @require_auth
    def sync_students_operations():
        """
        DEPRECATED: Trigger a manual sync from Google Sheets to Firestore cache.
        This endpoint is deprecated as we no longer merge data.
        """
        try:
            logger.warning("DEPRECATED: /admin/students/operations/sync endpoint is deprecated. No sync needed for separate Register/Survey data.")
            return jsonify({
                "success": False,
                "message": "This endpoint is deprecated. Register and Survey data are now separate and do not require syncing.",
            }), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error handling sync request: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed: {str(e)}"}), 500

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
        """DEPRECATED: Get all students data, metrics, and status. Use /admin/students/register or /admin/students/survey instead."""
        try:
            logger.warning("DEPRECATED: /admin/students/operations/all endpoint is deprecated. Use /admin/students/register or /admin/students/survey instead.")
            return jsonify({"error": "This endpoint is deprecated. Use /admin/students/register or /admin/students/survey instead."}), 410
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error in deprecated endpoint: {str(e)}", exc_info=True
            )
            return jsonify({"error": f"Failed: {str(e)}"}), 500

    @api.route("/admin/students/operations/emails", methods=["GET"])
    @require_auth
    def get_students_operations_emails():
        """Export student emails from Register and Survey forms as comma-separated list."""
        try:
            if not sheets_manager:
                return jsonify({"error": "Google Sheets manager not configured"}), 500

            # Get emails from both Register and Survey
            register_students = sheets_manager.get_register_students(force_refresh=False)
            survey_students = sheets_manager.get_survey_students(force_refresh=False)

            emails = []
            seen_emails = set()
            
            # Add Register emails
            for student in register_students:
                email = get_student_email(student)
                if email and email.lower() not in seen_emails:
                    emails.append(email)
                    seen_emails.add(email.lower())
            
            # Add Survey emails (avoid duplicates)
            for student in survey_students:
                email = get_student_email(student)
                if email and email.lower() not in seen_emails:
                    emails.append(email)
                    seen_emails.add(email.lower())

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


