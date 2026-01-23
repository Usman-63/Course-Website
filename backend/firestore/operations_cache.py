"""
Firestore-backed cache for student operations data.

This module provides:
- Sanitization utilities to make arbitrary Python/JSON-ish data Firestore-safe.
- A simple sync-lock mechanism to prevent concurrent heavy sync jobs.
- Helpers to read/write cached student list, optional detail docs, and metrics.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import firestore

from core.logger import logger


def _get_firestore_client() -> Optional[firestore.Client]:
    """Return a Firestore client if Firebase Admin is initialized, else None."""
    try:
        if not firebase_admin._apps:
            logger.warning("Firebase Admin not initialized; Firestore cache disabled")
            return None
        return firestore.client()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to get Firestore client: {exc}", exc_info=True)
        return None


def sanitize_for_firestore(obj: Any) -> Any:
    """
    Recursively sanitize an object so it can be stored in Firestore.

    - datetime / pandas Timestamp -> ISO 8601 string
    - float('nan'), float('inf'), float('-inf') -> None
    - numpy scalars -> underlying Python scalars
    - Other types are returned unchanged if JSON-serializable.
    """
    # Lazy import to avoid hard dependency if pandas/numpy are not used
    try:  # pragma: no cover - best-effort
        import pandas as pd  # type: ignore
        import numpy as np  # type: ignore
    except Exception:  # pragma: no cover - defensive
        pd = None  # type: ignore
        np = None  # type: ignore

    # Simple types first
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj

    # Floats / NaN / inf
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # Datetime-like
    if isinstance(obj, datetime):
        # Ensure timezone-aware in UTC
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.isoformat()

    if "Timestamp" in type(obj).__name__ and hasattr(obj, "to_pydatetime"):
        # pandas.Timestamp or similar
        dt = obj.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    # Numpy scalars / arrays
    if "numpy" in str(type(obj)):
        try:
            # numpy scalar
            if hasattr(obj, "item"):
                return sanitize_for_firestore(obj.item())
        except Exception:  # pragma: no cover - defensive
            return None

    # dict
    if isinstance(obj, dict):
        return {str(k): sanitize_for_firestore(v) for k, v in obj.items()}

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_firestore(v) for v in obj]

    # Fallback: string representation
    return str(obj)


# ---------------------------------------------------------------------------
# Sync status / lock helpers
# ---------------------------------------------------------------------------

SYNC_COLLECTION = "operations_sync"
SYNC_STATUS_DOC = "status"


def get_sync_status() -> Dict[str, Any]:
    """Return the current sync status document, or defaults if missing."""
    client = _get_firestore_client()
    if not client:
        return {
            "status": "DISABLED",
            "started_at": None,
            "finished_at": None,
            "last_error": "Firestore client not available",
        }

    doc_ref = client.collection(SYNC_COLLECTION).document(SYNC_STATUS_DOC)
    snap = doc_ref.get()
    if not snap.exists:
        return {
            "status": "IDLE",
            "started_at": None,
            "finished_at": None,
            "last_error": None,
        }
    data = snap.to_dict() or {}
    return data


def set_sync_status(status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Set the sync status document to the given status and details."""
    client = _get_firestore_client()
    if not client:
        return

    payload: Dict[str, Any] = {"status": status}
    if details:
        payload.update(details)

    # Sanitize before storing
    payload = sanitize_for_firestore(payload)

    client.collection(SYNC_COLLECTION).document(SYNC_STATUS_DOC).set(payload, merge=True)


def acquire_sync_lock(max_age_minutes: int = 15) -> bool:
    """
    Try to acquire a sync lock.

    Returns True if lock acquired, False if another sync is in progress.
    """
    client = _get_firestore_client()
    if not client:
        # If Firestore is unavailable, we can't coordinate; allow sync to proceed.
        logger.warning("Firestore not available, proceeding without sync lock")
        return True

    doc_ref = client.collection(SYNC_COLLECTION).document(SYNC_STATUS_DOC)
    now = datetime.now(timezone.utc)

    @firestore.transactional
    def _tx(transaction, ref):
        snap = ref.get(transaction=transaction)
        data = snap.to_dict() if snap.exists else {}
        status = data.get("status", "IDLE")
        started_at_raw = data.get("started_at")

        # Parse started_at if it's a string
        started_at = None
        if isinstance(started_at_raw, str):
            try:
                started_at = datetime.fromisoformat(started_at_raw)
            except Exception:
                started_at = None

        too_recent = False
        if started_at and isinstance(started_at, datetime):
            delta = now - started_at.replace(tzinfo=timezone.utc)
            too_recent = delta.total_seconds() < max_age_minutes * 60

        if status == "IN_PROGRESS" and too_recent:
            return False

        new_data = {
            "status": "IN_PROGRESS",
            "started_at": now.isoformat(),
            "finished_at": None,
            "last_error": None,
        }
        transaction.set(ref, sanitize_for_firestore(new_data), merge=True)
        return True

    try:
        transaction = client.transaction()
        acquired = _tx(transaction, doc_ref)
        return acquired
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to acquire sync lock: {exc}", exc_info=True)
        # Fail closed to prevent concurrent syncs if Firestore is having issues
        # This prevents race conditions when the database is unstable
        return False


def release_sync_lock(success: bool, error: Optional[str] = None) -> None:
    """Release the sync lock, recording success or error."""
    client = _get_firestore_client()
    if not client:
        return

    now = datetime.now(timezone.utc).isoformat()
    data: Dict[str, Any] = {
        "finished_at": now,
    }
    if success:
        data["status"] = "IDLE"
        data["last_error"] = None
    else:
        data["status"] = "ERROR"
        data["last_error"] = str(error) if error else "Unknown error"

    client.collection(SYNC_COLLECTION).document(SYNC_STATUS_DOC).set(
        sanitize_for_firestore(data), merge=True
    )


# ---------------------------------------------------------------------------
# Students + metrics cache
# ---------------------------------------------------------------------------

STUDENTS_LIST_COLLECTION = "operations_students_list"
STUDENTS_LIST_MAIN_DOC = "main"

STUDENTS_DETAIL_COLLECTION = "operations_students_detail"

METRICS_COLLECTION = "operations_metrics"
METRICS_LATEST_DOC = "latest"


def sync_students_to_firestore(students: List[Dict[str, Any]], metrics: Dict[str, Any]) -> bool:
    """
    Write merged student data and metrics to Firestore.

    - Students list: stored as a single document for efficient reads at small scale.
    - Metrics: stored in a dedicated document with last_synced timestamp.
    """
    client = _get_firestore_client()
    if not client:
        logger.warning("Skipping Firestore sync: client not available")
        return False

    try:
        now = datetime.now(timezone.utc)

        # Sanitize payloads
        students_payload = sanitize_for_firestore(students)
        metrics_payload = sanitize_for_firestore(
            {
                **(metrics or {}),
                "last_synced": now.isoformat(),
            }
        )

        batch = client.batch()

        # Students list (compressed view; we currently store full dicts)
        list_doc_ref = client.collection(STUDENTS_LIST_COLLECTION).document(
            STUDENTS_LIST_MAIN_DOC
        )
        batch.set(
            list_doc_ref,
            {
                "students": students_payload,
                "updated_at": now.isoformat(),
            },
        )

        # Metrics
        metrics_doc_ref = client.collection(METRICS_COLLECTION).document(
            METRICS_LATEST_DOC
        )
        batch.set(metrics_doc_ref, metrics_payload)

        batch.commit()
        logger.info(
            f"Synced {len(students)} students and metrics to Firestore operations cache"
        )
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to sync students to Firestore: {exc}", exc_info=True)
        return False


def get_students_list_from_firestore() -> Optional[List[Dict[str, Any]]]:
    """Return cached students list from Firestore, or None if not present."""
    client = _get_firestore_client()
    if not client:
        return None

    try:
        doc_ref = client.collection(STUDENTS_LIST_COLLECTION).document(
            STUDENTS_LIST_MAIN_DOC
        )
        snap = doc_ref.get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        students = data.get("students")
        if not isinstance(students, list):
            return None
        return students
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Error reading students list from Firestore: {exc}", exc_info=True)
        return None


def get_student_detail_from_firestore(email: str) -> Optional[Dict[str, Any]]:
    """Return detailed student document by normalized email, if present."""
    client = _get_firestore_client()
    if not client:
        return None

    norm_email = (email or "").strip().lower()
    if not norm_email:
        return None

    try:
        doc_ref = client.collection(STUDENTS_DETAIL_COLLECTION).document(norm_email)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return snap.to_dict() or {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Error reading student detail from Firestore: {exc}", exc_info=True)
        return None


def get_metrics_from_firestore() -> Optional[Dict[str, Any]]:
    """Return cached metrics document, or None if not present."""
    client = _get_firestore_client()
    if not client:
        return None

    try:
        doc_ref = client.collection(METRICS_COLLECTION).document(METRICS_LATEST_DOC)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return snap.to_dict() or {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Error reading metrics from Firestore: {exc}", exc_info=True)
        return None


def clear_firestore_cache() -> bool:
    """Clear all operations-related Firestore cache collections."""
    client = _get_firestore_client()
    if not client:
        return False

    try:
        # Helper to delete all docs in a collection
        def _clear_collection(coll_name: str):
            coll_ref = client.collection(coll_name)
            docs = coll_ref.stream()
            batch = client.batch()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count >= 400:  # safety batch size
                    batch.commit()
                    batch = client.batch()
                    count = 0
            if count:
                batch.commit()

        for coll in [
            STUDENTS_LIST_COLLECTION,
            STUDENTS_DETAIL_COLLECTION,
            METRICS_COLLECTION,
        ]:
            _clear_collection(coll)

        logger.info("Cleared Firestore operations cache collections")
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Error clearing Firestore cache: {exc}", exc_info=True)
        return False


