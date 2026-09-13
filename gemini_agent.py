
import os
import hashlib
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq


# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================
# CHECK API KEYS
# ============================================

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in .env file")
    raise RuntimeError("GEMINI_API_KEY is missing from .env")


if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY not found in .env file")
    raise RuntimeError("GROQ_API_KEY is missing from .env")


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
# GROQ CLIENT
# ============================================

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq fallback client initialized")

except Exception as e:
    print(f"❌ Failed to initialize Groq client: {e}")
    raise


# ============================================
# MODELS
# ============================================

GEMINI_MODEL_NAME = "gemini-3.8-flash"
GROQ_MODEL_NAME = "openai/gpt-oss-120b"

print(f"✅ Using Gemini model: {GEMINI_MODEL_NAME}")
print(f"✅ Using Groq fallback model: {GROQ_MODEL_NAME}")


# ============================================
# CACHE SETTINGS
# ============================================

CACHE_FILE = "response_cache.json"
CACHE_DURATION_HOURS = 24


def load_cache():
    """Load saved responses from cache."""

    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return {}


def save_cache(cache):
    """Save responses to cache."""

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
    """Create a unique cache key."""

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
    """Return cached response if still valid."""

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
            del cache[cache_key]
            save_cache(cache)

    except Exception:
        return None

    return None


def cache_response(cache_key, response):
    """Store a response in cache."""

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
    "foods",
    "eat",
    "eating",
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
    """Check whether a query is health-related."""

    query_lower = query.lower()

    for keyword in HEALTH_KEYWORDS:

        if keyword in query_lower:
            return True

    return False


# ============================================
# CONVERSATION HISTORY
# ============================================

def format_conversation_history(conversation_history):
    """Convert conversation history into readable text."""

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
# LANGUAGE INSTRUCTION
# ============================================

def get_language_instruction(language):
    """Return instructions for the selected language."""

    if language.lower() == "urdu":

        return """
Respond primarily in simple Urdu.
You may use common English medical terms
when they make the explanation clearer.
"""

    elif language.lower() == "hindi":

        return """
Respond primarily in simple Hindi.
You may use common English medical terms
when they make the explanation clearer.
"""

    elif language.lower() == "arabic":

        return """
Respond primarily in simple Arabic.
You may use common English medical terms
when they make the explanation clearer.
"""

    else:

        return """
Respond in clear, simple English.
"""


# ============================================
# HEALTH AI SYSTEM INSTRUCTION
# ============================================

def get_health_system_instruction(
    age_group,
    language
):
    """Create shared safety instructions for Gemini and Groq."""

    language_instruction = get_language_instruction(
        language
    )

    return f"""
You are a responsible AI Health Education Assistant.

Your purpose is to provide SAFE, CLEAR, SHORT,
and GENERAL health education.

IMPORTANT SAFETY RULES:

1. Never diagnose the user.

2. Never claim certainty about a medical condition.

3. Never replace a doctor or qualified healthcare professional.

4. Explain possible causes using careful language such as
   "may", "can", or "could".

5. Give practical and generally safe self-care information.

6. Do not provide prescription medication recommendations.

7. Do not provide medication dosages.

8. If medications are mentioned, keep the information general
   and advise the user to consult a doctor or pharmacist.

9. Clearly identify emergency warning signs.

10. If the user describes potentially life-threatening symptoms,
    immediately recommend contacting local emergency services
    or going to the nearest emergency medical facility.

11. Do not automatically mention "911".
    Use "local emergency services" unless the user specifies
    their country.

12. Do not create unnecessary fear.

13. Use simple language suitable for beginners.

14. Respect the selected age group:
    {age_group}

15. Respect the selected language:
    {language}

{language_instruction}

RESPONSE LENGTH:

Keep normal answers concise.

For simple questions, aim for approximately 150–400 words.

For more complex health questions, stay below approximately
700 words unless additional detail is genuinely necessary.

RESPONSE STYLE:

Use clear Markdown headings and bullet points.

For simple questions, prefer:

### 🩺 General Information

Brief explanation.

### What You Can Do

3–7 practical points.

### When to Seek Medical Help

Important warning signs.

### 🚨 Emergency

Only include this section when emergency symptoms or
serious warning signs are relevant.

### Important

A short reminder that this is educational information
and does not replace professional medical care.

Do not force every section when it is not relevant.

Always prioritize safety, clarity, and usefulness.
"""


# ============================================
# GROQ FALLBACK
# ============================================

def run_groq_fallback(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None
):
    """
    Use Groq as a fallback when Gemini is unavailable.
    """

    if conversation_history is None:
        conversation_history = []

    print("🔄 Switching to Groq fallback...")

    system_instruction = get_health_system_instruction(
        age_group=age_group,
        language=language
    )

    messages = [
        {
            "role": "system",
            "content": system_instruction
        }
    ]

    # Add conversation history
    for message in conversation_history:

        role = message.get("role", "")
        content = message.get("content", "")

        if role in ["user", "assistant"] and content:

            messages.append({
                "role": role,
                "content": content
            })

    # Add current question
    messages.append({
        "role": "user",
        "content": user_input
    })

    # ========================================
    # GROQ REQUEST
    # ========================================

    try:

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=messages,
            temperature=0.4,
            max_tokens=900
        )

        result = response.choices[0].message.content

        if not result:

            raise RuntimeError(
                "Groq returned an empty response."
            )

        print("✅ Groq fallback response received!")

        return result

    except Exception as e:

        print(f"❌ Groq fallback failed: {e}")

        return (
            "⚠️ Both Gemini and the fallback AI service "
            "are currently unavailable.\n\n"
            "Please try again later."
        )


# ============================================
# MAIN GEMINI FUNCTION WITH SMART RETRY
# ============================================

def run_gemini_with_retry(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None
):
    """
    Run Gemini with smart retry handling.

    If Gemini quota is exceeded,
    automatically use Groq fallback.
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

            error_text = str(e)

            print(
                f"⚠️ Gemini request failed "
                f"(attempt {attempt + 1}/{max_retries}): {e}"
            )

            # ========================================
            # QUOTA ERROR → GROQ FALLBACK
            # ========================================

            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
                or "quota exceeded" in error_text.lower()
            ):

                print("🚫 Gemini API quota exceeded.")
                print("⏸️ Stopping Gemini retries.")
                print("🔄 Activating Groq fallback...")

                return run_groq_fallback(
                    user_input=user_input,
                    age_group=age_group,
                    language=language,
                    conversation_history=conversation_history
                )

            # ========================================
            # TEMPORARY SERVER ERROR
            # ========================================

            if "503" in error_text or "UNAVAILABLE" in error_text:

                if attempt < max_retries - 1:

                    wait_time = 2 ** attempt

                    print(
                        "⏳ Temporary Gemini server issue."
                    )

                    print(
                        f"⏳ Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

                print(
                    "⚠️ Gemini remained unavailable."
                )

                print(
                    "🔄 Activating Groq fallback..."
                )

                return run_groq_fallback(
                    user_input=user_input,
                    age_group=age_group,
                    language=language,
                    conversation_history=conversation_history
                )

            # ========================================
            # OTHER ERRORS
            # ========================================

            if attempt < max_retries - 1:

                wait_time = 2 ** attempt

                print(
                    f"⏳ Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:

                print(
                    "⚠️ Gemini failed after all retries."
                )

                print(
                    "🔄 Activating Groq fallback..."
                )

                return run_groq_fallback(
                    user_input=user_input,
                    age_group=age_group,
                    language=language,
                    conversation_history=conversation_history
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
    """Send the health question to Gemini."""

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
    # SYSTEM INSTRUCTION
    # ========================================

    system_instruction = get_health_system_instruction(
        age_group=age_group,
        language=language
    )

    # ========================================
    # USER PROMPT
    # ========================================

    prompt = f"""
Previous conversation:

{history_text}

Current user question:

{user_input}

Answer the user's health question using the safety rules
provided in the system instructions.

Keep the response concise and beginner-friendly.

For a simple question:
- Give the most useful information first.
- Avoid unnecessary background information.
- Use short paragraphs and bullet points.

For symptom questions:
- Explain common possibilities without diagnosing.
- Give safe general self-care information.
- Mention important warning signs.
- Clearly identify emergency situations.

Do not provide prescription treatment or medication dosages.

Do not force unnecessary sections.

End with a short educational disclaimer.
"""

    # ========================================
    # GEMINI API REQUEST
    # ========================================

    print("Sending request to Gemini...")

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=900
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
    print("Testing Gemini + Groq Health Agent")
    print("========================================\n")

    test_question = "What are common symptoms of flu?"

    response = run_gemini_with_retry(
        user_input=test_question,
        age_group="Adults",
        language="English",
        conversation_history=[]
    )

    print("\n--- Final Response ---\n")
    print(response)