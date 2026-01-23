import re
import json

def parse_course_format(text_content):
    """
    Parse courseformat.txt and convert to JSON structure
    """
    lines = text_content.split('\n')
    
    data = {
        "modules": [],
        "links": [],
        "metadata": {
            "schedule": "",
            "capstone": "",
            "certification": "",
            "pricing": {
                "standard": 0,
                "student": 0
            },
            "earlyAccessOffer": ""
        }
    }
    
    current_module = None
    current_section = None
    collecting_topics = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Module detection
        module_match = re.match(r'Module (\d+):\s*(.+)', line)
        if module_match:
            # Save previous module if exists
            if current_module:
                data["modules"].append(current_module)
            
            module_num = module_match.group(1)
            module_title = module_match.group(2)
            current_module = {
                "id": module_num,
                "title": f"Module {module_num}: {module_title}",
                "hours": 0,
                "focus": "",
                "topics": [],
                "order": int(module_num)
            }
            collecting_topics = False
            i += 1
            continue
        
        # Hours and Focus
        if current_module and "Hours:" in line:
            hours_match = re.search(r'Hours:\s*(\d+)', line)
            focus_match = re.search(r'Focus:\s*(.+)', line)
            
            if hours_match:
                current_module["hours"] = int(hours_match.group(1))
            if focus_match:
                current_module["focus"] = focus_match.group(1).strip()
            i += 1
            continue
        
        # Topics section
        if current_module and "Topics Covered:" in line:
            collecting_topics = True
            i += 1
            continue
        
        # Collect topics until next module or section
        if current_module and collecting_topics:
            if line and not line.startswith("Module") and not line.startswith("Fellowship"):
                # Clean up topic line
                topic = line.strip()
                if topic and not topic.startswith("Hours:") and not topic.startswith("Focus:"):
                    current_module["topics"].append(topic)
            else:
                collecting_topics = False
        
        # Fellowship Logistics
        if "Fellowship Logistics" in line:
            if current_module:
                data["modules"].append(current_module)
                current_module = None
            i += 1
            continue
        
        # Schedule
        if "Schedule:" in line:
            schedule_text = line.replace("Schedule:", "").strip()
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line:
                    schedule_text += " " + next_line
            data["metadata"]["schedule"] = schedule_text
            i += 2
            continue
        
        # Capstone Project
        if "Capstone Project:" in line:
            capstone_text = line.replace("Capstone Project:", "").strip()
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line:
                    capstone_text += " " + next_line
            data["metadata"]["capstone"] = capstone_text
            i += 2
            continue
        
        # Certification
        if "Certification:" in line:
            cert_text = line.replace("Certification:", "").strip()
            data["metadata"]["certification"] = cert_text
            i += 1
            continue
        
        # Pricing
        if "Pricing & Enrollment" in line or "Category" in line:
            i += 1
            continue
        
        if "Standard" in line and "$" in lines[i + 2] if i + 2 < len(lines) else False:
            price_line = lines[i + 2].strip()
            price_match = re.search(r'\$([\d.]+)', price_line)
            if price_match:
                data["metadata"]["pricing"]["standard"] = float(price_match.group(1))
            i += 3
            continue
        
        if "Student" in line and "$" in lines[i + 2] if i + 2 < len(lines) else False:
            price_line = lines[i + 2].strip()
            price_match = re.search(r'\$([\d.]+)', price_line)
            if price_match:
                data["metadata"]["pricing"]["student"] = float(price_match.group(1))
            i += 3
            continue
        
        # Early access offer
        if "Early access offer" in line:
            data["metadata"]["earlyAccessOffer"] = line
            i += 1
            continue
        
        i += 1
    
    # Save last module
    if current_module:
        data["modules"].append(current_module)
    
    return data

def parse_course_format_file(file_path):
    """Parse course format from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return parse_course_format(content)

