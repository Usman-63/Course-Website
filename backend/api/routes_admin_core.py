"""
Admin core routes: authentication and course/module management.
"""
import time
import uuid
from typing import Callable, Optional

from flask import Blueprint, jsonify, request

from core.auth import (
    check_rate_limit,
    clear_login_attempts,
    create_custom_token,
    create_jwt_token,
    get_client_ip,
    require_auth,
    verify_password,
)
from core.logger import logger
from core.validators import ValidationError, validate_course_data, validate_module
from firestore.operations_cache import clear_firestore_cache
from firestore.admin_data import sync_assignment_fields_to_lab_count
from firestore.course_data import (
    get_course_data as get_course_data_from_firestore,
    update_course_data as update_course_data_to_firestore,
    course_data_exists,
)
from students.student_helpers import get_total_labs_count


def register_admin_core_routes(
    api: Blueprint,
    normalize_course_data: Callable[[dict], dict],
    sheets_manager: Optional[object] = None,
) -> None:
    """Register admin auth + course/module CRUD routes on the given blueprint."""

    @api.route("/admin/login", methods=["POST"])
    def admin_login():
        """Verify admin password and return JWT token."""
        try:
            # Check rate limiting
            if not check_rate_limit():
                logger.warning(f"Rate limit exceeded for IP: {get_client_ip()}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Too many login attempts. Please try again later.",
                        }
                    ),
                    429,
                )

            data = request.get_json() or {}
            password = data.get("password", "")

            if verify_password(password):
                # Clear failed login attempts
                clear_login_attempts(get_client_ip())

                # Create JWT token
                jwt_token = create_jwt_token()

                # Create a Firebase custom token for the admin
                # We use a fixed UID for the admin to simplify permissions
                firebase_token = create_custom_token("admin-user")

                logger.info(f"Admin login successful from IP: {get_client_ip()}")

                response = {
                    "success": True,
                    "message": "Login successful",
                    "token": jwt_token,  # JWT token for API authentication
                    "firebase_token": firebase_token,  # Firebase token for real-time features
                }
                return jsonify(response), 200
            else:
                # Record failed login attempt
                from core.auth import record_failed_login

                record_failed_login()
                logger.warning(f"Failed login attempt from IP: {get_client_ip()}")
                return jsonify({"success": False, "error": "Invalid password"}), 401
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error in admin login: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @api.route("/admin/firebase-token", methods=["GET"])
    @require_auth
    def get_firebase_token():
        """Get a fresh Firebase custom token for authenticated admin."""
        try:
            firebase_token = create_custom_token("admin-user")
            if not firebase_token:
                # If token creation failed (e.g. no creds), return 200 with null to avoid client errors
                # The client will just have to live without Firebase or show the error
                return jsonify({"firebase_token": None}), 200

            return jsonify({"firebase_token": firebase_token}), 200
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/data", methods=["GET"])
    @require_auth
    def get_admin_data():
        """Get full course data (admin view)."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            normalized = normalize_course_data(data)
            return jsonify(normalized), 200
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/courses", methods=["POST"])
    @require_auth
    def add_course():
        """Add new course."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            req_data = request.get_json() or {}
            if "title" not in req_data:
                return jsonify({"error": "Title is required"}), 400

            new_course = {
                "id": str(uuid.uuid4()),
                "title": req_data["title"],
                "isVisible": req_data.get("isVisible", False),  # Default hidden
                "modules": [],
                "links": [],
                "metadata": {
                    "schedule": "",
                    "pricing": {"standard": 0, "student": 0},
                },
            }

            data["courses"].append(new_course)
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            return jsonify({"success": True, "course": new_course}), 201
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/courses/<course_id>", methods=["PUT"])
    @require_auth
    def update_course(course_id):
        """Update course metadata (title, visibility, metadata)."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            req_data = request.get_json() or {}

            course_found = False
            for course in data["courses"]:
                if course["id"] == course_id:
                    if "title" in req_data:
                        course["title"] = req_data["title"]
                    if "isVisible" in req_data:
                        course["isVisible"] = req_data["isVisible"]
                    if "metadata" in req_data:
                        course["metadata"] = req_data["metadata"]
                    course_found = True
                    break

            if not course_found:
                return jsonify({"error": "Course not found"}), 404

            data["version"] = int(time.time() * 1000)
            
            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            return jsonify({"success": True, "message": "Course updated"}), 200
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/courses/<course_id>", methods=["DELETE"])
    @require_auth
    def delete_course(course_id):
        """Delete a course."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            # Check if course exists
            course_exists = any(course["id"] == course_id for course in data["courses"])

            if not course_exists:
                return jsonify({"error": "Course not found"}), 404

            # Filter out the course to delete
            data["courses"] = [c for c in data["courses"] if c["id"] != course_id]

            # Update version
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            return (
                jsonify({"success": True, "message": "Course deleted successfully"}),
                200,
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error deleting course: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @api.route("/admin/data", methods=["PUT"])
    @require_auth
    def update_course_data():
        """Update entire course data JSON."""
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "Request body is required"}), 400

            # Validate course data
            try:
                validate_course_data(data)
            except ValidationError as e:
                logger.warning(f"Course data validation failed: {str(e)}")
                return jsonify({"error": f"Validation failed: {str(e)}"}), 400

            # Update version
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            logger.info("Course data updated successfully")
            return (
                jsonify(
                    {"success": True, "message": "Course data updated successfully"}
                ),
                200,
            )
        except ValidationError as e:  # pragma: no cover - defensive
            return jsonify({"error": f"Validation failed: {str(e)}"}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error updating course data: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @api.route("/admin/modules", methods=["POST"])
    @require_auth
    def add_module():
        """Add new module."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            new_module = request.get_json()

            if not new_module:
                return jsonify({"error": "Request body is required"}), 400

            course_id = request.args.get("courseId")
            target_course = None

            if not data["courses"]:
                return jsonify({"error": "No courses found"}), 500

            if course_id:
                for course in data["courses"]:
                    if course["id"] == course_id:
                        target_course = course
                        break
                if not target_course:
                    return jsonify({"error": "Course not found"}), 404
            else:
                # Default to first course
                target_course = data["courses"][0]

            # Validate module data
            try:
                validate_module(new_module)
            except ValidationError as e:
                logger.warning(f"Module validation failed: {str(e)}")
                return jsonify({"error": f"Validation failed: {str(e)}"}), 400

            new_module["id"] = str(uuid.uuid4())

            # Set order if not provided
            if "order" not in new_module:
                new_module["order"] = len(target_course["modules"]) + 1

            target_course["modules"].append(new_module)
            target_course["modules"].sort(key=lambda x: x.get("order", 0))

            # Update version
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            logger.info(
                f'Module added: {new_module["id"]} to course {target_course["id"]}'
            )
            return jsonify({"success": True, "module": new_module}), 201
        except ValidationError as e:  # pragma: no cover - defensive
            return jsonify({"error": f"Validation failed: {str(e)}"}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error adding module: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @api.route("/admin/modules/<module_id>", methods=["PUT"])
    @require_auth
    def update_module(module_id):
        """Update module."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            updated_module = request.get_json()

            if not updated_module:
                return jsonify({"error": "Request body is required"}), 400

            course_id = request.args.get("courseId")
            target_course = None

            if not data["courses"]:
                return jsonify({"error": "No courses found"}), 500

            if course_id:
                for course in data["courses"]:
                    if course["id"] == course_id:
                        target_course = course
                        break
                if not target_course:
                    return jsonify({"error": "Course not found"}), 404
            else:
                # Default to first course
                target_course = data["courses"][0]

            # Find existing module first to support partial updates
            existing_module_index = -1
            for i, module in enumerate(target_course["modules"]):
                if module["id"] == module_id:
                    existing_module_index = i
                    break

            if existing_module_index == -1:
                logger.warning(f"Module not found: {module_id}")
                return jsonify({"error": "Module not found"}), 404

            # Merge existing module with updates
            merged_module = target_course["modules"][existing_module_index].copy()
            merged_module.update(updated_module)
            merged_module["id"] = module_id  # Ensure ID doesn't change

            # Validate merged module data
            try:
                validate_module(merged_module)
            except ValidationError as e:
                logger.warning(f"Module validation failed: {str(e)}")
                return jsonify({"error": f"Validation failed: {str(e)}"}), 400

            # Update the module in the list
            target_course["modules"][existing_module_index] = merged_module

            target_course["modules"].sort(key=lambda x: x.get("order", 0))

            # Update version
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            logger.info(f"Module updated: {module_id}")
            return jsonify({"success": True, "module": updated_module}), 200
        except ValidationError as e:  # pragma: no cover - defensive
            return jsonify({"error": f"Validation failed: {str(e)}"}), 400
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error updating module: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500


    @api.route("/admin/modules/<module_id>", methods=["DELETE"])
    @require_auth
    def delete_module(module_id):
        """Delete module."""
        try:
            data = get_course_data_from_firestore()
            
            if not data:
                return jsonify({"error": "Course data not available"}), 500

            data = normalize_course_data(data)

            course_id = request.args.get("courseId")
            target_course = None

            if not data["courses"]:
                return jsonify({"error": "No courses found"}), 500

            if course_id:
                for course in data["courses"]:
                    if course["id"] == course_id:
                        target_course = course
                        break
                if not target_course:
                    return jsonify({"error": "Course not found"}), 404
            else:
                # Default to first course
                target_course = data["courses"][0]

            target_course["modules"] = [
                m for m in target_course["modules"] if m["id"] != module_id
            ]

            # Reorder remaining modules
            for i, module in enumerate(target_course["modules"]):
                module["order"] = i + 1

            # Update version
            data["version"] = int(time.time() * 1000)

            if not update_course_data_to_firestore(data):
                return jsonify({"error": "Failed to save course data"}), 500
            
            # Invalidate caches and sync assignment fields
            _invalidate_caches_and_sync_fields(sheets_manager)
            
            return (
                jsonify({"success": True, "message": "Module deleted successfully"}),
                200,
            )
        except Exception as e:  # pragma: no cover - defensive
            return jsonify({"error": str(e)}), 500


def _invalidate_caches_and_sync_fields(sheets_manager: Optional[object]) -> None:
    """
    Helper function to invalidate all caches and sync assignment fields after course data changes.
    
    This ensures:
    1. Lab count cache is cleared
    2. Student data caches are cleared
    3. Firestore operations cache is cleared
    4. Assignment fields are synced to match current lab count
    """
    try:
        # Clear GoogleSheetsManager caches
        if sheets_manager and hasattr(sheets_manager, 'invalidate_all_caches'):
            sheets_manager.invalidate_all_caches()
            logger.debug("Invalidated GoogleSheetsManager caches")
        
        # Clear Firestore operations cache
        try:
            clear_firestore_cache()
            logger.debug("Cleared Firestore operations cache")
        except Exception as e:
            logger.warning(f"Failed to clear Firestore cache: {e}")
        
        # Sync assignment fields to match current lab count
        try:
            sync_stats = sync_assignment_fields_to_lab_count()
            logger.info(
                f"Synced assignment fields: {sync_stats['updated']} students updated "
                f"({sync_stats['added']} fields added, {sync_stats['removed']} fields removed)"
            )
        except Exception as e:
            logger.warning(f"Failed to sync assignment fields: {e}")
                
    except Exception as e:
        logger.error(f"Error invalidating caches: {e}", exc_info=True)
        # Don't fail the request if cache invalidation fails


