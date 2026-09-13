# =========================================================
# HEALTH INFORMATION TOOL
# =========================================================

def search_symptom_information(
    symptom: str,
    age_group: str = "All Ages"
) -> str:
    """
    Lightweight health-information tool.

    This is educational information only.
    It does not diagnose medical conditions.
    """

    symptom = symptom.lower().strip()
    age_group = age_group.lower().strip()

    base_info = {

        "diabetes":
            "Diabetes is a condition involving blood sugar regulation. "
            "Common concerns can include increased thirst, frequent urination, "
            "fatigue, and changes in weight.",

        "headache":
            "A headache is pain or discomfort in the head or surrounding areas. "
            "Causes can include stress, dehydration, lack of sleep, illness, "
            "or other conditions.",

        "fever":
            "Fever is an increase in body temperature that can occur with "
            "infections and other health conditions.",

        "cough":
            "A cough is a protective reflex that helps clear the airways. "
            "It can occur with infections, allergies, irritation, or other causes.",

        "cold":
            "The common cold is usually a mild respiratory illness that can "
            "cause a runny nose, congestion, cough, and sore throat.",

        "flu":
            "Flu is a respiratory illness that can cause fever, cough, "
            "body aches, fatigue, and other symptoms.",

        "dizziness":
            "Dizziness can describe lightheadedness, imbalance, or a feeling "
            "that the surroundings are moving.",

        "nausea":
            "Nausea is a feeling of discomfort in the stomach that may make "
            "a person feel like vomiting.",

        "fatigue":
            "Fatigue is a feeling of unusual tiredness or lack of energy.",

        "rash":
            "A rash is a change in the appearance or texture of the skin. "
            "Many different conditions can cause rashes."
    }

    age_guidance = {

        "children":
            "For children, monitor behavior, appetite, hydration, activity "
            "level, and changes from their normal condition.",

        "teens":
            "For teenagers, consider sleep, nutrition, stress, mental "
            "well-being, school demands, and social factors.",

        "adults":
            "For adults, consider sleep, hydration, nutrition, stress, "
            "physical activity, and work-life balance.",

        "seniors":
            "For older adults, consider existing health conditions, "
            "medications, hydration, mobility, and fall risk.",

        "elderly":
            "For elderly people, gentle care, hydration, mobility, "
            "comfort, and fall prevention are important considerations."
    }

    information = base_info.get(
        symptom,
        "General health information about this topic."
    )

    guidance = age_guidance.get(
        age_group,
        ""
    )

    if guidance:

        return (
            f"General Information:\n{information}\n\n"
            f"Age-Specific Guidance:\n{guidance}\n\n"
            "This information is educational and does not provide a diagnosis."
        )

    return (
        f"General Information:\n{information}\n\n"
        "This information is educational and does not provide a diagnosis."
    )