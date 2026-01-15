"""Input validation for API endpoints"""
from typing import Any, Dict, List, Optional
from flask import jsonify

class ValidationError(Exception):
    """Custom validation error"""
    pass

def validate_module(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate module data"""
    errors = []
    
    # Required fields
    if 'title' not in data or not data['title'] or not isinstance(data['title'], str):
        errors.append('title is required and must be a non-empty string')
    
    if 'hours' not in data:
        errors.append('hours is required')
    elif not isinstance(data['hours'], (int, float)) or data['hours'] < 0:
        errors.append('hours must be a non-negative number')
    
    if 'focus' not in data or not data['focus'] or not isinstance(data['focus'], str):
        errors.append('focus is required and must be a non-empty string')
    
    # Optional but validated fields
    if 'topics' in data:
        if not isinstance(data['topics'], list):
            errors.append('topics must be a list')
        elif not all(isinstance(topic, str) for topic in data['topics']):
            errors.append('all topics must be strings')
    
    if 'order' in data and not isinstance(data['order'], int):
        errors.append('order must be an integer')
    
    if 'labCount' in data and (not isinstance(data['labCount'], int) or data['labCount'] < 0):
        errors.append('labCount must be a non-negative integer')
    
    if 'videoLink' in data and data['videoLink'] and not isinstance(data['videoLink'], str):
        errors.append('videoLink must be a string')
    
    if 'labLink' in data and data['labLink'] and not isinstance(data['labLink'], str):
        errors.append('labLink must be a string')
    
    if errors:
        raise ValidationError('; '.join(errors))
    
    return data

def validate_course_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate course data structure"""
    errors = []
    
    # Check if this is the new multi-course structure
    if 'courses' in data:
        if not isinstance(data['courses'], list):
            errors.append('courses must be a list')
        else:
            for i, course in enumerate(data['courses']):
                if 'id' not in course:
                    errors.append(f'Course {i} must have an id')
                if 'title' not in course:
                    errors.append(f'Course {i} must have a title')
                
                # Validate modules within the course
                for j, module in enumerate(course.get('modules', [])):
                    try:
                        validate_module(module)
                    except ValidationError as e:
                        errors.append(f'Course {i} Module {j}: {str(e)}')
    else:
        # Legacy single-course structure
        if 'modules' not in data or not isinstance(data['modules'], list):
            errors.append('modules is required and must be a list')
        
        if 'metadata' not in data or not isinstance(data['metadata'], dict):
            errors.append('metadata is required and must be an object')
        
        # Validate each module
        for i, module in enumerate(data.get('modules', [])):
            try:
                validate_module(module)
            except ValidationError as e:
                errors.append(f'Module {i}: {str(e)}')
    
    if errors:
        raise ValidationError('; '.join(errors))
    
    return data

