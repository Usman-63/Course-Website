"""
Firestore-backed storage for course structure data.

This module replaces Google Drive storage for course data with Firestore:
- course_data: Stores the entire course structure (courses, modules, links, metadata, version)

The data structure matches the normalized format:
{
    "version": int (timestamp),
    "courses": [
        {
            "id": str,
            "title": str,
            "isVisible": bool,
            "modules": [...],
            "links": [...],
            "metadata": {...}
        }
    ]
}
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import time

import firebase_admin
from firebase_admin import firestore

from core.logger import logger
from firestore.operations_cache import sanitize_for_firestore

# Collection and document names
COURSE_DATA_COLLECTION = "course_data"
COURSE_DATA_DOCUMENT_ID = "main"  # Single document stores all course data


def _get_firestore_client() -> Optional[firestore.Client]:
    """Return a Firestore client if Firebase Admin is initialized, else None."""
    try:
        if not firebase_admin._apps:
            logger.warning("Firebase Admin not initialized; Firestore course data disabled")
            return None
        return firestore.client()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to get Firestore client: {exc}", exc_info=True)
        return None


def get_course_data() -> Optional[Dict[str, Any]]:
    """
    Read course data from Firestore.
    
    Returns:
        Course data dict with 'version' and 'courses' keys, or None if not found/error
    """
    client = _get_firestore_client()
    if not client:
        return None
    
    try:
        doc_ref = client.collection(COURSE_DATA_COLLECTION).document(COURSE_DATA_DOCUMENT_ID)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.debug("Course data document not found in Firestore")
            return None
        
        data = doc.to_dict() or {}
        
        # Ensure required structure exists
        if "courses" not in data:
            data["courses"] = []
        if "version" not in data:
            data["version"] = int(time.time() * 1000)
        
        return data
    except Exception as exc:
        logger.error(f"Error reading course data from Firestore: {exc}", exc_info=True)
        return None


def update_course_data(data: Dict[str, Any]) -> bool:
    """
    Write course data to Firestore.
    
    Args:
        data: Course data dict with 'version' and 'courses' keys
        
    Returns:
        True if successful, False otherwise
    """
    client = _get_firestore_client()
    if not client:
        logger.error("Firestore client not available")
        return False
    
    try:
        # Ensure version is set
        if "version" not in data:
            data["version"] = int(time.time() * 1000)
        
        # Ensure courses array exists
        if "courses" not in data:
            data["courses"] = []
        
        # Sanitize data for Firestore (handles None values, etc.)
        sanitized_data = sanitize_for_firestore(data)
        
        # Write to Firestore
        doc_ref = client.collection(COURSE_DATA_COLLECTION).document(COURSE_DATA_DOCUMENT_ID)
        doc_ref.set(sanitized_data, merge=False)  # Replace entire document
        
        logger.info(f"Course data updated in Firestore (version: {data.get('version')})")
        return True
    except Exception as exc:
        logger.error(f"Error writing course data to Firestore: {exc}", exc_info=True)
        return False


def course_data_exists() -> bool:
    """
    Check if course data exists in Firestore.
    
    Returns:
        True if course data document exists, False otherwise
    """
    client = _get_firestore_client()
    if not client:
        return False
    
    try:
        doc_ref = client.collection(COURSE_DATA_COLLECTION).document(COURSE_DATA_DOCUMENT_ID)
        doc = doc_ref.get()
        return doc.exists
    except Exception as exc:
        logger.error(f"Error checking course data existence: {exc}", exc_info=True)
        return False
