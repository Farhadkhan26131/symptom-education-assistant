"""
Long-Term Memory (Module 2)
============================
Manages a permanent user profile that persists across sessions.
Based on the mem0/LangMem pattern from Module 2.
"""

import json
import os
from datetime import datetime

PROFILE_DIR = "profiles"
PROFILE_FILE = os.path.join(PROFILE_DIR, "user_profile.json")

DEFAULT_PROFILE = {
    "user_id": "default_user",
    "name": "",
    "age_group": "Adults",
    "language": "English",
    "chronic_conditions": [],
    "allergies": [],
    "medications": [],
    "past_topics": [],
    "preferences": {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}


def _ensure_dir():
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR, exist_ok=True)


def load_profile():
    """Load the persistent user profile from disk."""
    _ensure_dir()
    if not os.path.exists(PROFILE_FILE):
        save_profile(DEFAULT_PROFILE)
        return DEFAULT_PROFILE.copy()
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROFILE.copy()


def save_profile(profile):
    """Save the user profile to disk."""
    _ensure_dir()
    profile["updated_at"] = datetime.now().isoformat()
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Profile save failed: {e}")
        return False


def update_profile_field(field, value):
    """Update a single field in the profile."""
    profile = load_profile()
    profile[field] = value
    save_profile(profile)
    return profile


def add_chronic_condition(condition):
    """Add a chronic condition to the profile."""
    profile = load_profile()
    if condition and condition not in profile["chronic_conditions"]:
        profile["chronic_conditions"].append(condition)
        save_profile(profile)
    return profile


def add_past_topic(topic):
    """Record a health topic the user has asked about."""
    profile = load_profile()
    if topic and topic not in profile["past_topics"]:
        profile["past_topics"].append(topic)
        # Keep only the last 20 topics
        profile["past_topics"] = profile["past_topics"][-20:]
        save_profile(profile)
    return profile


def get_profile_context():
    """
    Return a formatted string of the user's profile
    to inject into the agent's prompt.
    """
    profile = load_profile()
    parts = []
    if profile.get("name"):
        parts.append(f"User's name: {profile['name']}")
    if profile.get("age_group"):
        parts.append(f"Age group: {profile['age_group']}")
    if profile.get("chronic_conditions"):
        parts.append(f"Known chronic conditions: {', '.join(profile['chronic_conditions'])}")
    if profile.get("allergies"):
        parts.append(f"Known allergies: {', '.join(profile['allergies'])}")
    if profile.get("medications"):
        parts.append(f"Current medications: {', '.join(profile['medications'])}")
    if profile.get("past_topics"):
        parts.append(f"Previously discussed health topics: {', '.join(profile['past_topics'][-5:])}")
    if not parts:
        return "No long-term user profile yet."
    return "LONG-TERM USER PROFILE:\n" + "\n".join(parts)


if __name__ == "__main__":
    print("Testing user_profile.py...")
    profile = load_profile()
    print(f"✅ Profile loaded: {profile['user_id']}")
    add_chronic_condition("diabetes")
    add_past_topic("headache")
    print("\nProfile context:")
    print(get_profile_context())
    print("\n✅ Test complete")