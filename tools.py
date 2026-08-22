# Expanded with age-specific data

def search_symptom_information(symptom: str, age_group: str = "All Ages") -> str:
    """Search for symptom information with age-specific details"""
    
    # Base information
    base_info = {
        "diabetes": "Diabetes affects blood sugar management",
        "headache": "Headache is pain in the head area",
        # ... add more
    }
    
    # Age-specific guidance
    age_guidance = {
        "children": "Watch for behavioral changes, appetite changes",
        "teens": "Monitor mental health impact, social life effects",
        "adults": "Work-life balance, stress management",
        "seniors": "Multiple conditions, medication interactions",
        "elderly": "Gentle care, fall prevention, comfort focus"
    }
    
    return base_info.get(symptom.lower(), "General information about this condition")