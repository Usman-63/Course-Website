"""
Firestore-backed storage for admin-generated student data.

This module replaces Google Sheets Admin_Logs with Firestore collections:
- admin_students: Stores grades, attendance, evaluations, payment/resume backups
- admin_classes: Stores class definitions for attendance tracking
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

import firebase_admin
from firebase_admin import firestore

from core.logger import logger
from firestore.operations_cache import sanitize_for_firestore

# Collection names
ADMIN_STUDENTS_COLLECTION = "admin_students"
ADMIN_CLASSES_COLLECTION = "admin_classes"


def _get_firestore_client() -> Optional[firestore.Client]:
    """Return a Firestore client if Firebase Admin is initialized, else None."""
    try:
        if not firebase_admin._apps:
            logger.warning("Firebase Admin not initialized; Firestore admin data disabled")
            return None
        return firestore.client()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to get Firestore client: {exc}", exc_info=True)
        return None


def _normalize_email(email: str) -> Optional[str]:
    """
    Normalize email to lowercase, trimmed (used as document ID).
    
    Args:
        email: Email address string
        
    Returns:
        Normalized email string, or None if email is empty/invalid after normalization
    """
    if not email or not isinstance(email, str):
        return None
    normalized = email.lower().strip()
    # Basic validation: must contain @ and have at least 3 characters (a@b minimum)
    if not normalized or len(normalized) < 3 or '@' not in normalized:
        return None
    return normalized


# ---------------------------------------------------------------------------
# Admin Students CRUD
# ---------------------------------------------------------------------------


def get_admin_student(email: str) -> Optional[Dict[str, Any]]:
    """
    Read single student admin data from Firestore by email.

    Args:
        email: Student email address

    Returns:
        Student admin data dict, or None if not found
    """
    client = _get_firestore_client()
    if not client:
        return None

    try:
        email_normalized = _normalize_email(email)
        if not email_normalized:
            logger.warning(f"Invalid or empty email provided: {email}")
            return None

        # Use normalized email as the document ID for deterministic lookups
        doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        # Ensure email field is present and normalized
        if "email" not in data or not data["email"]:
            data["email"] = email_normalized

        data["_id"] = doc.id  # Include document ID (email)
        return data
    except Exception as exc:
        logger.error(f"Error reading admin student {email}: {exc}", exc_info=True)
        return None


def get_all_admin_students() -> Dict[str, Dict[str, Any]]:
    """
    Read all admin student documents from Firestore.

    Returns:
        Dict mapping normalized email -> admin data dict
    """
    client = _get_firestore_client()
    if not client:
        return {}

    try:
        students_ref = client.collection(ADMIN_STUDENTS_COLLECTION)
        docs = students_ref.stream()

        result = {}
        for doc in docs:
            data = doc.to_dict()
            if data:
                # Email field is required - skip documents without it
                email = _normalize_email(data.get("email", ""))
                if not email:
                    logger.warning(f"Admin student document {doc.id} missing required email field, skipping")
                    continue
                
                data["email"] = email
                data["_id"] = doc.id  # Include document ID
                result[email] = data

        logger.debug(f"Read {len(result)} admin students from Firestore")
        return result
    except Exception as exc:
        logger.error(f"Error reading all admin students: {exc}", exc_info=True)
        return {}


def create_admin_student(
    email: str, initial_data: Optional[Dict[str, Any]] = None, course_module_structure: Optional[Dict[str, Dict[str, int]]] = None
) -> bool:
    """
    Create new admin student document with default values.

    Args:
        email: Student email address
        initial_data: Optional initial data (name, paymentScreenshot, etc.)
        course_module_structure: Dict mapping course_id -> {module_id -> lab_count}
            If None, will fetch from Firestore course data

    Returns:
        True if successful, False otherwise
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return False

    try:
        email_normalized = _normalize_email(email)
        if not email_normalized:
            logger.error(f"Invalid or empty email address: {email}")
            return False

        # Check if student already exists
        existing = get_admin_student(email)
        if existing:
            logger.debug(f"Admin student already exists: {email}")
            # If exists, sync assignment fields to match current course structure
            if course_module_structure:
                _sync_assignment_fields_for_student(email_normalized, course_module_structure, existing)
            return True  # Already exists

        # Get course/module structure if not provided
        if course_module_structure is None:
            from firestore.course_data import get_course_data as get_course_data_from_firestore
            from students.student_helpers import get_course_module_structure
            course_data = get_course_data_from_firestore()
            course_module_structure = get_course_module_structure(course_data)

        # Build default document
        now = datetime.now(timezone.utc)
        doc_data: Dict[str, Any] = {
            # Store normalized email both as field and as document ID
            "email": email_normalized,
            "attendance": {},
            "assignmentGrades": {},
            "teacherEvaluation": "",
            "createdAt": now,
            "updatedAt": now,
        }

        # Initialize empty assignment grades per course/module
        for course_id, modules in course_module_structure.items():
            doc_data["assignmentGrades"][course_id] = {}
            for module_id, lab_count in modules.items():
                doc_data["assignmentGrades"][course_id][module_id] = {}
                for lab_num in range(1, lab_count + 1):
                    doc_data["assignmentGrades"][course_id][module_id][f"lab{lab_num}"] = ""

        # Merge with initial_data if provided
        if initial_data:
            # Handle name
            if "name" in initial_data or "Name" in initial_data:
                doc_data["name"] = initial_data.get("name") or initial_data.get("Name")

            # Handle payment screenshot
            if "paymentScreenshot" in initial_data or "Payment Screenshot" in initial_data:
                doc_data["paymentScreenshot"] = (
                    initial_data.get("paymentScreenshot")
                    or initial_data.get("Payment Screenshot")
                )

            # Handle resume link
            if "resumeLink" in initial_data or "Resume Link" in initial_data:
                doc_data["resumeLink"] = (
                    initial_data.get("resumeLink") or initial_data.get("Resume Link")
                )

        # Sanitize before writing
        doc_data = sanitize_for_firestore(doc_data)

        # Write to Firestore using normalized email as the document ID
        # Use merge=True to prevent overwriting if document was created concurrently
        doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)
        doc_ref.set(doc_data, merge=True)

        logger.info(f"Created admin student document: {email} (ID: {email_normalized})")
        return True
    except Exception as exc:
        logger.error(f"Error creating admin student {email}: {exc}", exc_info=True)
        return False


def _sync_assignment_fields_for_student(
    email_normalized: str,
    course_module_structure: Dict[str, Dict[str, int]],
    existing_data: Dict[str, Any]
) -> None:
    """
    Sync assignment fields for a single student to match course/module structure.
    
    Args:
        email_normalized: Normalized email (document ID)
        course_module_structure: Dict mapping course_id -> {module_id -> lab_count}
        existing_data: Existing student data
    """
    client = _get_firestore_client()
    if not client:
        return
    
    try:
        existing_grades = existing_data.get('assignmentGrades', {})
        if not isinstance(existing_grades, dict):
            existing_grades = {}
        
        updated_grades = {}
        needs_update = False
        
        # Build new structure based on course/module structure
        for course_id, modules in course_module_structure.items():
            updated_grades[course_id] = {}
            for module_id, lab_count in modules.items():
                updated_grades[course_id][module_id] = {}
                
                # Preserve existing grades if they exist
                existing_course = existing_grades.get(course_id, {})
                existing_module = existing_course.get(module_id, {}) if isinstance(existing_course, dict) else {}
                
                for lab_num in range(1, lab_count + 1):
                    lab_key = f"lab{lab_num}"
                    # Preserve existing grade if available
                    if isinstance(existing_module, dict) and lab_key in existing_module:
                        updated_grades[course_id][module_id][lab_key] = existing_module[lab_key]
                    else:
                        updated_grades[course_id][module_id][lab_key] = ""
                        needs_update = True
        
        # Check if structure changed (removed courses/modules)
        for course_id in existing_grades.keys():
            if course_id not in course_module_structure:
                needs_update = True
                break
            existing_course = existing_grades.get(course_id, {})
            if isinstance(existing_course, dict):
                for module_id in existing_course.keys():
                    if module_id not in course_module_structure.get(course_id, {}):
                        needs_update = True
                        break
        
        if needs_update:
            doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)
            doc_ref.update({
                'assignmentGrades': updated_grades,
                'updatedAt': datetime.now(timezone.utc)
            })
            logger.debug(f"Synced assignment fields for student: {email_normalized}")
    except Exception as exc:
        logger.error(f"Error syncing assignment fields for {email_normalized}: {exc}", exc_info=True)


def _convert_old_format_to_new_format(
    old_format_grades: Dict[str, str],
    course_module_structure: Dict[str, Dict[str, int]]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Convert old format assignment grades (Assignment N Grade) to new per-course/module structure.
    
    Args:
        old_format_grades: Dict mapping "Assignment N Grade" -> grade value
        course_module_structure: Dict mapping course_id -> {module_id -> lab_count}
        
    Returns:
        New format structure: {course_id: {module_id: {lab1: grade, lab2: grade, ...}}}
    """
    new_format = {}
    assignment_num = 1
    
    for course_id, modules in course_module_structure.items():
        new_format[course_id] = {}
        for module_id, lab_count in modules.items():
            new_format[course_id][module_id] = {}
            for lab_num in range(1, lab_count + 1):
                grade_key = f"Assignment {assignment_num} Grade"
                grade_value = old_format_grades.get(grade_key, "")
                new_format[course_id][module_id][f"lab{lab_num}"] = str(grade_value) if grade_value else ""
                assignment_num += 1
    
    return new_format


def _deep_merge_assignment_grades(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge assignment grades, preserving existing structure and updating with new values.
    
    Args:
        existing: Existing assignment grades structure
        new: New assignment grades to merge
        
    Returns:
        Merged assignment grades structure
    """
    result = existing.copy() if isinstance(existing, dict) else {}
    
    if not isinstance(new, dict):
        return result
    
    for course_id, modules in new.items():
        if course_id not in result:
            result[course_id] = {}
        
        if isinstance(modules, dict):
            for module_id, labs in modules.items():
                if module_id not in result[course_id]:
                    result[course_id][module_id] = {}
                
                if isinstance(labs, dict):
                    for lab_key, grade_value in labs.items():
                        result[course_id][module_id][lab_key] = grade_value
    
    return result


def update_admin_student(email: str, updates: Dict[str, Any]) -> bool:
    """
    Update specific fields for an admin student.

    Args:
        email: Student email address
        updates: Dictionary of fields to update
            - attendance: dict (will be merged with existing)
            - assignmentGrades: dict (will be merged with existing)
            - teacherEvaluation: string
            - paymentScreenshot: string
            - resumeLink: string
            - name: string

    Returns:
        True if successful, False otherwise
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return False

    try:
        email_normalized = _normalize_email(email)
        if not email_normalized:
            logger.error(f"Invalid or empty email address: {email}")
            return False

        # Find or create document by email
        student_data = get_admin_student(email)
        if not student_data:
            logger.warning(f"Admin student not found for email: {email}. Creating new document.")
            # Create the document if it doesn't exist
            if create_admin_student(email, {}):
                student_data = get_admin_student(email)
            else:
                logger.error(f"Failed to create admin student document for: {email}")
                return False

        # Use normalized email as document ID for updates
        doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)
        existing_doc = doc_ref.get()

        update_data: Dict[str, Any] = {
            "updatedAt": datetime.now(timezone.utc),
        }

        # Handle attendance merge
        if "Attendance" in updates or "attendance" in updates:
            attendance = updates.get("Attendance") or updates.get("attendance")
            if isinstance(attendance, dict):
                # Merge with existing attendance if present
                if existing_doc.exists:
                    existing_data = existing_doc.to_dict() or {}
                    existing_attendance = existing_data.get("attendance", {})
                    if isinstance(existing_attendance, dict):
                        existing_attendance.update(attendance)
                        attendance = existing_attendance
                update_data["attendance"] = attendance
            elif isinstance(attendance, str):
                # If it's a JSON string, try to parse it
                try:
                    import json

                    attendance_dict = json.loads(attendance)
                    if existing_doc.exists:
                        existing_data = existing_doc.to_dict() or {}
                        existing_attendance = existing_data.get("attendance", {})
                        if isinstance(existing_attendance, dict):
                            existing_attendance.update(attendance_dict)
                            attendance_dict = existing_attendance
                    update_data["attendance"] = attendance_dict
                except Exception:
                    logger.warning(f"Could not parse attendance JSON: {attendance}")
                    update_data["attendance"] = {}

        # Handle assignment grades - support both old and new formats
        if "assignmentGrades" in updates:
            # New format: per-course/module structure
            new_grades = updates.get("assignmentGrades")
            if isinstance(new_grades, dict):
                if existing_doc.exists:
                    existing_data = existing_doc.to_dict() or {}
                    existing_grades = existing_data.get("assignmentGrades", {})
                    if isinstance(existing_grades, dict):
                        # Deep merge: preserve existing structure and update with new values
                        merged_grades = _deep_merge_assignment_grades(existing_grades, new_grades)
                        update_data["assignmentGrades"] = merged_grades
                    else:
                        update_data["assignmentGrades"] = new_grades
                else:
                    update_data["assignmentGrades"] = new_grades
        
        # Handle old format: "Assignment N Grade" fields (for backward compatibility)
        assignment_updates_old_format = {}
        for key, value in updates.items():
            if key.startswith("Assignment") and "Grade" in key:
                # Convert old format to new format
                # Extract assignment number from "Assignment N Grade"
                try:
                    assignment_num = int(key.replace("Assignment ", "").replace(" Grade", ""))
                    # We need course/module context - for now, store in a temporary structure
                    # This will be properly structured when syncing
                    assignment_updates_old_format[key] = str(value) if value is not None else ""
                except ValueError:
                    pass
        
        # If we have old format updates, convert them to new format and merge
        if assignment_updates_old_format:
            if existing_doc.exists:
                existing_data = existing_doc.to_dict() or {}
                existing_grades = existing_data.get("assignmentGrades", {})
                
                # Check if existing structure is old format (flat) or new format (nested)
                is_old_format = any(
                    key.startswith("Assignment") and "Grade" in key 
                    for key in existing_grades.keys() if isinstance(existing_grades, dict)
                )
                
                if is_old_format:
                    # Merge old format with old format
                    if isinstance(existing_grades, dict):
                        existing_grades.update(assignment_updates_old_format)
                        update_data["assignmentGrades"] = existing_grades
                else:
                    # Old format updates but new format structure - convert to new format
                    from firestore.course_data import get_course_data as get_course_data_from_firestore
                    from students.student_helpers import get_course_module_structure
                    course_data = get_course_data_from_firestore()
                    course_module_structure = get_course_module_structure(course_data)
                    
                    if course_module_structure:
                        # Convert old format to new format
                        converted_grades = _convert_old_format_to_new_format(
                            assignment_updates_old_format,
                            course_module_structure
                        )
                        
                        # Deep merge with existing new format structure
                        merged_grades = _deep_merge_assignment_grades(existing_grades, converted_grades)
                        update_data["assignmentGrades"] = merged_grades
                    else:
                        # No course structure available, keep old format temporarily
                        logger.warning(f"Received old format assignment updates but no course structure available. Storing in old format.")
                        if isinstance(existing_grades, dict):
                            existing_grades.update(assignment_updates_old_format)
                            update_data["assignmentGrades"] = existing_grades
                        else:
                            update_data["assignmentGrades"] = assignment_updates_old_format
            else:
                # New student, convert to new format if course structure available
                from firestore.course_data import get_course_data as get_course_data_from_firestore
                from students.student_helpers import get_course_module_structure
                course_data = get_course_data_from_firestore()
                course_module_structure = get_course_module_structure(course_data)
                
                if course_module_structure:
                    converted_grades = _convert_old_format_to_new_format(
                        assignment_updates_old_format,
                        course_module_structure
                    )
                    update_data["assignmentGrades"] = converted_grades
                else:
                    # No course structure, use old format
                    update_data["assignmentGrades"] = assignment_updates_old_format

        # Handle other fields
        field_mapping = {
            "Teacher Evaluation": "teacherEvaluation",
            "teacherEvaluation": "teacherEvaluation",
            "Payment Screenshot": "paymentScreenshot",
            "paymentScreenshot": "paymentScreenshot",
            "Resume Link": "resumeLink",
            "resumeLink": "resumeLink",
            "Name": "name",
            "name": "name",
        }

        for key, firestore_key in field_mapping.items():
            if key in updates:
                update_data[firestore_key] = updates[key]

        # Sanitize before writing
        update_data = sanitize_for_firestore(update_data)

        # Update document
        doc_ref.update(update_data)

        logger.info(f"Updated admin student: {email}")
        return True
    except Exception as exc:
        logger.error(f"Error updating admin student {email}: {exc}", exc_info=True)
        return False


def bulk_update_admin_students(updates: List[Dict[str, Any]], course_module_structure: Optional[Dict[str, Dict[str, int]]] = None) -> Dict[str, Any]:
    """
    Batch update multiple admin students.

    Args:
        updates: List of update dicts, each with 'email' key and field updates
        course_module_structure: Optional course/module structure for creating missing students
            If None, will fetch from Firestore course data

    Returns:
        Dict with stats: {'success': bool, 'updated': int, 'failed': int, 'skipped': int}
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return {'success': False, 'updated': 0, 'failed': 0, 'skipped': 0}

    if not updates:
        return {'success': True, 'updated': 0, 'failed': 0, 'skipped': 0}

    # Get course/module structure if not provided
    if course_module_structure is None:
        from firestore.course_data import get_course_data as get_course_data_from_firestore
        from students.student_helpers import get_course_module_structure
        course_data = get_course_data_from_firestore()
        course_module_structure = get_course_module_structure(course_data)
    
    stats = {'updated': 0, 'failed': 0, 'skipped': 0}

    try:
        # Firestore batch limit is 500 operations
        batch_size = 500
        total_batches = (len(updates) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min(batch_start + batch_size, len(updates))
            batch_updates = updates[batch_start:batch_end]

            batch = client.batch()
            batch_count = 0

            for update in batch_updates:
                email = update.get("email")
                if not email:
                    logger.warning("Update missing email, skipping")
                    stats['skipped'] += 1
                    continue

                email_normalized = _normalize_email(email)
                if not email_normalized:
                    logger.warning(f"Invalid email in update: {email}, skipping")
                    stats['skipped'] += 1
                    continue

                # Ensure document exists (create if missing)
                student_data = get_admin_student(email)
                if not student_data:
                    logger.warning(f"Admin student not found for email: {email}. Creating new document.")
                    # Create the document if it doesn't exist
                    if not create_admin_student(email, {}, course_module_structure=course_module_structure):
                        logger.error(f"Failed to create admin student document for: {email}, skipping update")
                        stats['failed'] += 1
                        continue

                doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)

                # Build update data (similar to update_admin_student logic)
                update_data: Dict[str, Any] = {
                    "updatedAt": datetime.now(timezone.utc),
                }

                # Handle attendance
                if "Attendance" in update or "attendance" in update:
                    attendance = update.get("Attendance") or update.get("attendance")
                    if isinstance(attendance, dict):
                        # Try to merge with existing
                        existing_doc = doc_ref.get()
                        if existing_doc.exists:
                            existing_data = existing_doc.to_dict() or {}
                            existing_attendance = existing_data.get("attendance", {})
                            if isinstance(existing_attendance, dict):
                                existing_attendance.update(attendance)
                                attendance = existing_attendance
                        update_data["attendance"] = attendance

                # Handle assignment grades - support both old and new formats
                if "assignmentGrades" in update:
                    # New format: per-course/module structure
                    new_grades = update.get("assignmentGrades")
                    if isinstance(new_grades, dict):
                        existing_doc = doc_ref.get()
                        if existing_doc.exists:
                            existing_data = existing_doc.to_dict() or {}
                            existing_grades = existing_data.get("assignmentGrades", {})
                            if isinstance(existing_grades, dict):
                                merged_grades = _deep_merge_assignment_grades(existing_grades, new_grades)
                                update_data["assignmentGrades"] = merged_grades
                            else:
                                update_data["assignmentGrades"] = new_grades
                        else:
                            update_data["assignmentGrades"] = new_grades
                
                # Handle old format: "Assignment N Grade" fields (for backward compatibility)
                assignment_updates_old_format = {}
                for key, value in update.items():
                    if key.startswith("Assignment") and "Grade" in key:
                        assignment_updates_old_format[key] = str(value) if value is not None else ""

                if assignment_updates_old_format:
                    existing_doc = doc_ref.get()
                    if existing_doc.exists:
                        existing_data = existing_doc.to_dict() or {}
                        existing_grades = existing_data.get("assignmentGrades", {})
                        
                        # Check if existing structure is old format (flat) or new format (nested)
                        is_old_format = any(
                            key.startswith("Assignment") and "Grade" in key 
                            for key in existing_grades.keys() if isinstance(existing_grades, dict)
                        )
                        
                        if is_old_format:
                            # Merge old format with old format
                            if isinstance(existing_grades, dict):
                                existing_grades.update(assignment_updates_old_format)
                                update_data["assignmentGrades"] = existing_grades
                        else:
                            # Old format updates but new format structure - convert to new format
                            if course_module_structure:
                                # Convert old format to new format
                                converted_grades = _convert_old_format_to_new_format(
                                    assignment_updates_old_format,
                                    course_module_structure
                                )
                                
                                # Deep merge with existing new format structure
                                merged_grades = _deep_merge_assignment_grades(existing_grades, converted_grades)
                                update_data["assignmentGrades"] = merged_grades
                            else:
                                # No course structure available, keep old format temporarily
                                logger.warning(f"Received old format assignment updates but no course structure available. Storing in old format.")
                                if isinstance(existing_grades, dict):
                                    existing_grades.update(assignment_updates_old_format)
                                    update_data["assignmentGrades"] = existing_grades
                                else:
                                    update_data["assignmentGrades"] = assignment_updates_old_format
                    else:
                        # New student, convert to new format if course structure available
                        if course_module_structure:
                            converted_grades = _convert_old_format_to_new_format(
                                assignment_updates_old_format,
                                course_module_structure
                            )
                            update_data["assignmentGrades"] = converted_grades
                        else:
                            # No course structure, use old format
                            update_data["assignmentGrades"] = assignment_updates_old_format

                # Handle other fields
                field_mapping = {
                    "Teacher Evaluation": "teacherEvaluation",
                    "teacherEvaluation": "teacherEvaluation",
                    "Payment Screenshot": "paymentScreenshot",
                    "paymentScreenshot": "paymentScreenshot",
                    "Resume Link": "resumeLink",
                    "resumeLink": "resumeLink",
                    "Name": "name",
                    "name": "name",
                }

                for key, firestore_key in field_mapping.items():
                    if key in update:
                        update_data[firestore_key] = update[key]

                # Sanitize and add to batch
                update_data = sanitize_for_firestore(update_data)
                batch.update(doc_ref, update_data)
                batch_count += 1
                stats['updated'] += 1

            # Commit batch if it has operations
            if batch_count > 0:
                try:
                    batch.commit()
                    logger.info(f"Bulk updated batch {batch_idx + 1}/{total_batches} ({batch_count} students)")
                except Exception as batch_exc:
                    logger.error(f"Error committing batch {batch_idx + 1}: {batch_exc}", exc_info=True)
                    stats['failed'] += batch_count
                    stats['updated'] -= batch_count

        logger.info(
            f"Bulk update completed: {stats['updated']} updated, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        return {
            'success': stats['failed'] == 0,
            'updated': stats['updated'],
            'failed': stats['failed'],
            'skipped': stats['skipped']
        }
    except Exception as exc:
        logger.error(f"Error in bulk update: {exc}", exc_info=True)
        return {'success': False, 'updated': stats['updated'], 'failed': stats['failed'] + len(updates) - stats['updated'] - stats['skipped'], 'skipped': stats['skipped']}


def sync_payment_backups_to_firestore(register_df) -> bool:
    """
    Sync payment screenshots and resume links from Register to Firestore admin_students.

    Args:
        register_df: pandas DataFrame from Register sheet

    Returns:
        True if sync completed (even if some updates failed), False on critical error
    """
    if register_df.empty:
        return True

    client = _get_firestore_client()
    if not client:
        logger.warning("Firestore client not available, skipping payment backup sync")
        return False

    try:
        import pandas as pd

        # Find Register columns
        payment_col = None
        resume_col = None

        for col in register_df.columns:
            col_lower = str(col).lower()
            if "payment" in col_lower and "screenshot" in col_lower:
                payment_col = col
            if "resume" in col_lower and ("upload" in col_lower or "link" in col_lower):
                resume_col = col

        if not payment_col and not resume_col:
            logger.debug("No payment/resume columns found in Register")
            return True

        # Find email column
        email_col = None
        for col in register_df.columns:
            if "email" in str(col).lower():
                email_col = col
                break

        if not email_col:
            logger.warning("No email column found in Register")
            return False

        # Get all existing admin students
        existing_students = get_all_admin_students()

        updates = []
        for _, row in register_df.iterrows():
            email = str(row.get(email_col, "")).strip()
            if not email:
                continue

            email_normalized = _normalize_email(email)
            student_data = existing_students.get(email_normalized, {})

            update_needed = False
            update_data: Dict[str, Any] = {"email": email_normalized}

            # Check payment screenshot
            if payment_col:
                payment_val = str(row.get(payment_col, "")).strip()
                if payment_val and payment_val.lower() != "nan":
                    if not student_data.get("paymentScreenshot"):
                        update_data["paymentScreenshot"] = payment_val
                        update_needed = True

            # Check resume link
            if resume_col:
                resume_val = str(row.get(resume_col, "")).strip()
                if resume_val and resume_val.lower() != "nan":
                    if not student_data.get("resumeLink"):
                        update_data["resumeLink"] = resume_val
                        update_needed = True

            if update_needed:
                updates.append(update_data)

        if updates:
            success = bulk_update_admin_students(updates)
            logger.info(f"Synced payment/resume backups for {len(updates)} students")
            return success

        return True
    except Exception as exc:
        logger.error(f"Error syncing payment backups: {exc}", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Admin Classes CRUD
# ---------------------------------------------------------------------------


def get_all_classes() -> List[Dict[str, Any]]:
    """
    Read all classes from Firestore.

    Returns:
        List of class dicts
    """
    client = _get_firestore_client()
    if not client:
        return []

    try:
        classes_ref = client.collection(ADMIN_CLASSES_COLLECTION)
        docs = classes_ref.stream()

        classes = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                data["_id"] = doc.id  # Include document ID
                classes.append(data)

        # Sort by date if available
        classes.sort(key=lambda x: x.get("date", ""), reverse=True)

        logger.debug(f"Read {len(classes)} classes from Firestore")
        return classes
    except Exception as exc:
        logger.error(f"Error reading classes: {exc}", exc_info=True)
        return []


def create_class(class_data: Dict[str, Any]) -> bool:
    """
    Add new class to Firestore.

    Args:
        class_data: Dict with id, date, topic, description

    Returns:
        True if successful, False otherwise
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return False

    try:
        # Generate ID if missing
        class_id = class_data.get("id")
        if not class_id:
            import uuid

            class_id = str(uuid.uuid4())
            class_data["id"] = class_id

        # Add timestamp
        class_data["createdAt"] = datetime.now(timezone.utc)

        # Sanitize
        class_data = sanitize_for_firestore(class_data)

        # Use class_id as document ID for easier lookup
        doc_ref = client.collection(ADMIN_CLASSES_COLLECTION).document(class_id)
        doc_ref.set(class_data, merge=False)

        logger.info(f"Created class: {class_data.get('topic')} ({class_id})")
        return True
    except Exception as exc:
        logger.error(f"Error creating class: {exc}", exc_info=True)
        return False


def delete_class(class_id: str) -> bool:
    """
    Delete class from Firestore.

    Args:
        class_id: Class identifier (document ID)

    Returns:
        True if deleted, False if not found or error
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return False

    try:
        doc_ref = client.collection(ADMIN_CLASSES_COLLECTION).document(class_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Class {class_id} not found")
            return False

        doc_ref.delete()
        logger.info(f"Deleted class: {class_id}")
        return True
    except Exception as exc:
        logger.error(f"Error deleting class {class_id}: {exc}", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Migration and Maintenance Functions
# ---------------------------------------------------------------------------


def sync_assignment_fields_to_lab_count(course_module_structure: Optional[Dict[str, Dict[str, int]]] = None) -> Dict[str, Any]:
    """
    Sync assignment grade fields for all students to match current course/module structure.
    
    This function:
    - Adds missing assignment fields for new courses/modules
    - Removes orphaned assignment fields for removed courses/modules
    - Preserves existing grades
    
    Args:
        course_module_structure: Dict mapping course_id -> {module_id -> lab_count}
            If None, will fetch from Firestore course data
        
    Returns:
        Dict with stats: {'added': count, 'removed': count, 'updated': count, 'errors': count}
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return {'added': 0, 'removed': 0, 'updated': 0, 'errors': 0}
    
    # Get course/module structure if not provided
    if course_module_structure is None:
        from firestore.course_data import get_course_data as get_course_data_from_firestore
        from students.student_helpers import get_course_module_structure
        course_data = get_course_data_from_firestore()
        course_module_structure = get_course_module_structure(course_data)
    
    if not course_module_structure:
        logger.info("No course/module structure found, skipping assignment field sync")
        return {'added': 0, 'removed': 0, 'updated': 0, 'errors': 0}
    
    stats = {'added': 0, 'removed': 0, 'updated': 0, 'errors': 0}
    
    try:
        # Get all admin students
        students_ref = client.collection(ADMIN_STUDENTS_COLLECTION)
        docs = students_ref.stream()
        
        batch = client.batch()
        batch_count = 0
        max_batch_size = 500  # Firestore batch limit
        
        for doc in docs:
            try:
                data = doc.to_dict()
                if not data:
                    continue
                
                # Use email from document data (which is the document ID) for consistency
                email_normalized = data.get('email', '')
                if not email_normalized:
                    # Fallback to document ID if email field is missing
                    email_normalized = doc.id
                
                existing_grades = data.get('assignmentGrades', {})
                if not isinstance(existing_grades, dict):
                    existing_grades = {}
                
                updated_grades = {}
                updated = False
                
                # Build new structure based on course/module structure
                for course_id, modules in course_module_structure.items():
                    updated_grades[course_id] = {}
                    for module_id, lab_count in modules.items():
                        updated_grades[course_id][module_id] = {}
                        
                        # Preserve existing grades if they exist
                        existing_course = existing_grades.get(course_id, {})
                        existing_module = existing_course.get(module_id, {}) if isinstance(existing_course, dict) else {}
                        
                        for lab_num in range(1, lab_count + 1):
                            lab_key = f"lab{lab_num}"
                            # Preserve existing grade if available
                            if isinstance(existing_module, dict) and lab_key in existing_module:
                                updated_grades[course_id][module_id][lab_key] = existing_module[lab_key]
                            else:
                                updated_grades[course_id][module_id][lab_key] = ""
                                updated = True
                                stats['added'] += 1
                
                # Check for removed courses/modules
                for course_id in existing_grades.keys():
                    if course_id not in course_module_structure:
                        updated = True
                        stats['removed'] += 1
                        continue
                    existing_course = existing_grades.get(course_id, {})
                    if isinstance(existing_course, dict):
                        for module_id in existing_course.keys():
                            if module_id not in course_module_structure.get(course_id, {}):
                                updated = True
                                stats['removed'] += 1
                
                # Update document if changes were made
                if updated:
                    # Use email_normalized (document ID) for consistency
                    doc_ref = client.collection(ADMIN_STUDENTS_COLLECTION).document(email_normalized)
                    batch.update(doc_ref, {
                        'assignmentGrades': updated_grades,
                        'updatedAt': datetime.now(timezone.utc)
                    })
                    batch_count += 1
                    stats['updated'] += 1
                    
                    # Commit batch if it reaches the limit
                    if batch_count >= max_batch_size:
                        try:
                            batch.commit()
                            logger.debug(f"Committed batch of {batch_count} updates")
                        except Exception as batch_error:
                            logger.error(f"Error committing batch: {batch_error}", exc_info=True)
                            stats['errors'] += batch_count
                        batch = client.batch()
                        batch_count = 0
                        
            except Exception as e:
                logger.error(f"Error processing student document {doc.id}: {e}", exc_info=True)
                stats['errors'] += 1
        
        # Commit remaining batch
        if batch_count > 0:
            try:
                batch.commit()
                logger.debug(f"Committed final batch of {batch_count} updates")
            except Exception as batch_error:
                logger.error(f"Error committing final batch: {batch_error}", exc_info=True)
                stats['errors'] += batch_count
        
        logger.info(
            f"Synced assignment fields: {stats['updated']} students updated "
            f"({stats['added']} fields added, {stats['removed']} fields removed, {stats['errors']} errors)"
        )
        return stats
        
    except Exception as exc:
        logger.error(f"Error syncing assignment fields: {exc}", exc_info=True)
        stats['errors'] += 1
        return stats

