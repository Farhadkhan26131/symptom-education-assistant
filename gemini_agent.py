import os
import hashlib
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in .env file")
    print("Please add:")
    print("GEMINI_API_KEY='your_api_key_here'")
    raise RuntimeError("GEMINI_API_KEY is missing from .env")


# ============================================
# GEMINI CLIENT
# ============================================

try:
    client = genai.Client(api_key=GEMINI_API_KEY)

    print("✅ Gemini client initialized")

except Exception as e:
    print(f"❌ Failed to initialize Gemini client: {e}")
    raise


# ============================================
# MODEL
# ============================================

MODEL_NAME = "gemini-3.8-flash"

print(f"✅ Using Gemini model: {MODEL_NAME}")


# ============================================
# CACHE SETTINGS
# ============================================

CACHE_FILE = "response_cache.json"

CACHE_DURATION_HOURS = 24


def load_cache():
    """
    Load saved responses from the cache file.
    """

    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return {}


def save_cache(cache):
    """
    Save responses to the cache file.
    """

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            json.dump(
                cache,
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:
        print(f"⚠️ Could not save cache: {e}")


def create_cache_key(
    user_input,
    age_group,
    language,
    conversation_history
):
    """
    Create a unique MD5 cache key.
    """

    cache_data = {
        "user_input": user_input,
        "age_group": age_group,
        "language": language,
        "conversation_history": conversation_history
    }

    cache_string = json.dumps(
        cache_data,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.md5(
        cache_string.encode("utf-8")
    ).hexdigest()


def get_cached_response(cache_key):
    """
    Return cached response if it is still valid.
    """

    cache = load_cache()

    if cache_key not in cache:
        return None

    cached_item = cache[cache_key]

    try:
        cached_time = datetime.fromisoformat(
            cached_item["timestamp"]
        )

        expiry_time = cached_time + timedelta(
            hours=CACHE_DURATION_HOURS
        )

        if datetime.now() < expiry_time:

            print("⚡ Using cached response")

            return cached_item["response"]

        else:
            # Remove expired cache entry
            del cache[cache_key]
            save_cache(cache)

    except Exception:
        return None

    return None


def cache_response(cache_key, response):
    """
    Store a response in the cache.
    """

    cache = load_cache()

    cache[cache_key] = {
        "timestamp": datetime.now().isoformat(),
        "response": response
    }

    save_cache(cache)


# ============================================
# HEALTH KEYWORDS
# ============================================

HEALTH_KEYWORDS = [
    # General health
    "health",
    "healthy",
    "symptom",
    "symptoms",
    "disease",
    "illness",
    "condition",
    "medical",
    "medicine",
    "doctor",
    "hospital",
    "clinic",
    "patient",

    # Common symptoms
    "pain",
    "headache",
    "fever",
    "cough",
    "cold",
    "flu",
    "sneeze",
    "sneezing",
    "fatigue",
    "tired",
    "weakness",
    "dizziness",
    "nausea",
    "vomiting",
    "diarrhea",
    "constipation",
    "stomach",
    "abdomen",
    "chest pain",
    "breathing",
    "breath",
    "shortness of breath",
    "heart",
    "heartbeat",
    "palpitation",

    # Common conditions
    "diabetes",
    "blood pressure",
    "hypertension",
    "asthma",
    "migraine",
    "allergy",
    "allergic",
    "infection",
    "virus",
    "bacteria",
    "covid",
    "pneumonia",
    "bronchitis",
    "anxiety",
    "stress",
    "depression",

    # Body parts
    "head",
    "eye",
    "ear",
    "nose",
    "throat",
    "neck",
    "shoulder",
    "arm",
    "hand",
    "leg",
    "foot",
    "back",
    "skin",
    "tooth",
    "teeth",

    # Health activities
    "exercise",
    "workout",
    "fitness",
    "diet",
    "nutrition",
    "food",
    "sleep",
    "weight",
    "water",
    "hydration",

    # Emergency
    "emergency",
    "severe",
    "bleeding",
    "unconscious",
    "fainting",
    "seizure",
    "stroke",
    "heart attack",

    # Medicine
    "tablet",
    "medicine",
    "medication",
    "dose",
    "dosage",
    "prescription",
    "drug",
    "antibiotic"
]


# ============================================
# HEALTH QUERY FILTER
# ============================================

def is_health_related(query):
    """
    Check whether a user query is related to health.
    """

    query_lower = query.lower()

    for keyword in HEALTH_KEYWORDS:

        if keyword in query_lower:
            return True

    return False


# ============================================
# CONVERSATION HISTORY
# ============================================

def format_conversation_history(conversation_history):
    """
    Convert conversation history into readable text.
    """

    if not conversation_history:
        return "No previous conversation."

    formatted_history = []

    for message in conversation_history:

        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            formatted_history.append(
                f"USER: {content}"
            )

        elif role == "assistant":
            formatted_history.append(
                f"ASSISTANT: {content}"
            )

    return "\n".join(formatted_history)


# ============================================
# MAIN GEMINI FUNCTION WITH RETRY
# ============================================

def run_gemini_with_retry(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None
):
    """
    Run Gemini with automatic retry.
    """

    if conversation_history is None:
        conversation_history = []

    max_retries = 3

    for attempt in range(max_retries):

        try:

            return run_gemini(
                user_input=user_input,
                age_group=age_group,
                language=language,
                conversation_history=conversation_history
            )

        except Exception as e:

            print(
                f"⚠️ Gemini request failed "
                f"(attempt {attempt + 1}/{max_retries}): {e}"
            )

            if attempt < max_retries - 1:

                wait_time = 2 ** attempt

                print(
                    f"⏳ Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:

                return (
                    "⚠️ Sorry, I could not process your request "
                    "right now. Please try again in a moment."
                )


# ============================================
# GEMINI REQUEST
# ============================================

def run_gemini(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None
):
    """
    Send the health question to Gemini.
    """

    if conversation_history is None:
        conversation_history = []


    # ========================================
    # FORMAT HISTORY
    # ========================================

    history_text = format_conversation_history(
        conversation_history
    )


    # ========================================
    # CACHE
    # ========================================

    cache_key = create_cache_key(
        user_input=user_input,
        age_group=age_group,
        language=language,
        conversation_history=conversation_history
    )

    cached_response = get_cached_response(
        cache_key
    )

    if cached_response:
        return cached_response


    # ========================================
    # HEALTH FILTER
    # ========================================

    if not is_health_related(user_input):

        return (
            "I am a health education assistant. "
            "Please ask me a health-related question "
            "about symptoms, diseases, prevention, "
            "nutrition, fitness, or general health."
        )


    # ========================================
    # LANGUAGE INSTRUCTIONS
    # ========================================

    language_instruction = ""

    if language.lower() == "urdu":

        language_instruction = """
Respond primarily in simple Urdu.
You may use common English medical terms
when they make the explanation clearer.
"""

    elif language.lower() == "hindi":

        language_instruction = """
Respond primarily in simple Hindi.
You may use common English medical terms
when they make the explanation clearer.
"""

    elif language.lower() == "arabic":

        language_instruction = """
Respond primarily in simple Arabic.
You may use common English medical terms
when they make the explanation clearer.
"""

    else:

        language_instruction = """
Respond in clear, simple English.
"""


    # ========================================
    # SYSTEM INSTRUCTION
    # ========================================

    system_instruction = f"""
You are a responsible AI Health Education Assistant.

Your purpose is to provide general health education
and symptom information.

IMPORTANT SAFETY RULES:

1. Do NOT diagnose the user.

2. Do NOT claim certainty about a medical condition.

3. Do NOT replace a doctor or qualified healthcare professional.

4. Explain possible causes or possibilities carefully.

5. For symptoms, explain common possible causes first,
   followed by less common but important possibilities
   when appropriate.

6. Clearly identify emergency warning signs.

7. If the user describes potentially life-threatening
   symptoms, advise them to seek emergency medical care
   immediately.

8. Never tell the user to ignore serious symptoms.

9. Do not recommend prescription medicines or specific
   prescription dosages.

10. For medications, provide general educational
    information and encourage consultation with a
    healthcare professional.

11. Use simple language suitable for a general audience.

12. Do not create unnecessary fear.

13. Do not provide a definitive diagnosis.

14. Respect the selected age group:
    {age_group}

15. Respect the selected language:
    {language}

{language_instruction}

For emergency symptoms such as severe chest pain,
difficulty breathing, severe bleeding, loss of consciousness,
stroke-like symptoms, or other potentially life-threatening
situations, clearly tell the user to contact local emergency
services or go to the nearest emergency medical facility.

Always include an appropriate reminder that the information
is educational and does not replace professional medical care.
"""


    # ========================================
    # USER PROMPT
    # ========================================

    prompt = f"""
Previous conversation:

{history_text}


Current user question:

{user_input}


Please answer the user's health question.

Use this structure when appropriate:

### Overview
Briefly explain the topic.

### Possible Causes
Explain common possible causes without diagnosing.

### Common Symptoms
List relevant symptoms.

### What You Can Do
Give safe general self-care or health information.

### When to Seek Medical Help
Explain warning signs and when professional care is needed.

### Important
Include a short medical disclaimer.

Do not force sections when they are not relevant.
Keep the response useful, clear, and reasonably concise.
"""


    # ========================================
    # GEMINI API REQUEST
    # ========================================

    print("Sending request to Gemini...")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=1200
        )
    )


    # ========================================
    # GET RESPONSE TEXT
    # ========================================

    result = response.text


    if not result:

        raise RuntimeError(
            "Gemini returned an empty response."
        )


    # ========================================
    # CACHE RESPONSE
    # ========================================

    cache_response(
        cache_key=cache_key,
        response=result
    )


    print("✅ Response received!")

    return result


# ============================================
# SIMPLE TEST
# ============================================

if __name__ == "__main__":

    print("\n========================================")
    print("Testing Gemini Health Agent")
    print("========================================\n")

    test_question = "What are common symptoms of flu?"

    response = run_gemini_with_retry(
        user_input=test_question,
        age_group="Adults",
        language="English",
        conversation_history=[]
    )

    print("\n--- Gemini Response ---\n")
    print(response)