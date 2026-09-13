import os
import hashlib
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in .env file")
    print("Please add:")
    print("GEMINI_API_KEY=YOUR_API_KEY")
    raise RuntimeError("GEMINI_API_KEY is missing from .env file")


# ============================================================
# GEMINI CLIENT
# ============================================================

try:

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    # Current Gemini model
    MODEL_NAME = "gemini-3.8-flash"

    print(f"✅ Gemini client initialized")
    print(f"✅ Using Gemini model: {MODEL_NAME}")

except Exception as e:

    print(f"❌ Failed to initialize Gemini client: {e}")

    raise RuntimeError(
        f"Gemini client initialization failed: {e}"
    ) from e


# ============================================================
# CACHE SYSTEM
# ============================================================

CACHE_FILE = "response_cache.json"


class ResponseCache:

    def __init__(self, cache_duration_hours=24):

        self.cache_duration = timedelta(
            hours=cache_duration_hours
        )

        self.cache = self.load()

    # --------------------------------------------------------
    # LOAD CACHE
    # --------------------------------------------------------

    def load(self):

        if os.path.exists(CACHE_FILE):

            try:

                with open(
                    CACHE_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:

                    return json.load(f)

            except Exception:

                return {}

        return {}

    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    def save(self):

        try:

            with open(
                CACHE_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.cache,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                f"⚠️ Could not save cache: {e}"
            )

    # --------------------------------------------------------
    # CREATE CACHE KEY
    # --------------------------------------------------------

    def get_key(
        self,
        query,
        age_group,
        language,
        conversation_history=None
    ):

        history_text = json.dumps(
            conversation_history or [],
            ensure_ascii=False,
            sort_keys=True
        )

        raw_key = (
            f"{query}|"
            f"{age_group}|"
            f"{language}|"
            f"{history_text}"
        )

        return hashlib.md5(
            raw_key.encode("utf-8")
        ).hexdigest()

    # --------------------------------------------------------
    # GET CACHE
    # --------------------------------------------------------

    def get(
        self,
        query,
        age_group,
        language,
        conversation_history=None
    ):

        key = self.get_key(
            query,
            age_group,
            language,
            conversation_history
        )

        if key not in self.cache:

            return None

        data = self.cache[key]

        try:

            timestamp = datetime.fromisoformat(
                data["timestamp"]
            )

            if (
                datetime.now() - timestamp
                < self.cache_duration
            ):

                return data["response"]

        except Exception:

            return None

        return None

    # --------------------------------------------------------
    # SET CACHE
    # --------------------------------------------------------

    def set(
        self,
        query,
        age_group,
        language,
        response,
        conversation_history=None
    ):

        key = self.get_key(
            query,
            age_group,
            language,
            conversation_history
        )

        self.cache[key] = {

            "response": response,

            "timestamp":
                datetime.now().isoformat()
        }

        self.save()


cache = ResponseCache()


# ============================================================
# HEALTH KEYWORDS
# ============================================================

HEALTH_KEYWORDS = [

    # --------------------------------------------------------
    # Symptoms
    # --------------------------------------------------------

    "symptom",
    "pain",
    "ache",
    "fever",
    "cough",
    "cold",
    "flu",
    "headache",
    "migraine",
    "dizzy",
    "dizziness",
    "vertigo",
    "lightheaded",
    "nausea",
    "vomit",
    "fatigue",
    "tired",
    "weakness",
    "swelling",
    "inflammation",
    "rash",
    "itching",
    "burning",
    "numbness",
    "tingling",
    "stiffness",

    # --------------------------------------------------------
    # Common Diseases
    # --------------------------------------------------------

    "diabetes",
    "hypertension",
    "high blood pressure",
    "heart disease",
    "asthma",
    "allergy",
    "sinusitis",
    "pneumonia",
    "copd",
    "bronchitis",
    "arthritis",
    "rheumatoid",
    "osteoarthritis",
    "gout",
    "osteoporosis",
    "fibromyalgia",
    "chronic",
    "acute",
    "depression",
    "anxiety",
    "stress",
    "panic",
    "ptsd",
    "bipolar",
    "schizophrenia",
    "ocd",
    "adhd",
    "autism",
    "alzheimer",
    "dementia",
    "memory loss",
    "forget",
    "forgetting",
    "parkinson",
    "multiple sclerosis",
    "epilepsy",
    "seizure",

    # --------------------------------------------------------
    # Infectious Diseases
    # --------------------------------------------------------

    "measles",
    "mumps",
    "rubella",
    "chickenpox",
    "polio",
    "tetanus",
    "diphtheria",
    "pertussis",
    "whooping cough",
    "hiv",
    "aids",
    "hepatitis",
    "typhoid",
    "cholera",
    "malaria",
    "dengue",
    "zika",
    "ebola",
    "covid",
    "corona",
    "influenza",
    "tuberculosis",
    "tb",
    "food poisoning",
    "food pois",
    "strep throat",
    "tonsillitis",
    "laryngitis",
    "pharyngitis",
    "gastroenteritis",
    "appendicitis",
    "pancreatitis",
    "peritonitis",
    "cellulitis",
    "abscess",
    "boil",
    "warts",
    "herpes",
    "shingles",
    "cold sore",
    "yeast infection",
    "thrush",
    "ringworm",
    "athlete foot",

    # --------------------------------------------------------
    # Body Parts
    # --------------------------------------------------------

    "heart",
    "lung",
    "kidney",
    "liver",
    "brain",
    "spine",
    "bone",
    "joint",
    "muscle",
    "nerve",
    "skin",
    "blood",
    "stomach",
    "intestine",
    "colon",
    "rectum",
    "bladder",
    "prostate",
    "ovary",
    "uterus",
    "cervix",
    "breast",
    "breast health",
    "testicle",
    "penis",
    "vagina",
    "pelvic",
    "shoulder",
    "knee",
    "hip",
    "ankle",
    "wrist",
    "elbow",
    "neck",
    "back",
    "chest",
    "chest pain",
    "abdomen",
    "head",
    "face",
    "eye",
    "ear",
    "nose",
    "throat",
    "mouth",
    "tooth",
    "gum",
    "hair",
    "hair loss",
    "hairfall",
    "bald",
    "balding",

    # --------------------------------------------------------
    # Medical Terms
    # --------------------------------------------------------

    "medical",
    "doctor",
    "hospital",
    "clinic",
    "pharmacy",
    "medicine",
    "pill",
    "tablet",
    "capsule",
    "syrup",
    "injection",
    "vaccine",
    "vaccination",
    "immunization",
    "antibiotic",
    "prescription",
    "diagnosis",
    "treatment",
    "therapy",
    "surgery",
    "operation",
    "emergency",
    "ambulance",
    "x-ray",
    "mri",
    "ct scan",
    "ultrasound",
    "biopsy",
    "screening",
    "checkup",
    "physical exam",
    "blood test",
    "urine test",
    "stool test",
    "pap smear",
    "mammogram",

    # --------------------------------------------------------
    # Health & Wellness
    # --------------------------------------------------------

    "health",
    "wellness",
    "fitness",
    "exercise",
    "diet",
    "nutrition",
    "vitamin",
    "mineral",
    "supplement",
    "herbal",
    "sleep",
    "insomnia",
    "rest",
    "relaxation",
    "meditation",
    "mental health",
    "emotional",
    "psychological",
    "pregnancy",
    "pregnant",
    "childbirth",
    "labor",
    "delivery",
    "breastfeeding",
    "lactation",
    "infant",
    "baby",
    "child",
    "elderly",
    "senior",
    "aging",
    "geriatric",

    # --------------------------------------------------------
    # Caregiving
    # --------------------------------------------------------

    "caregiver",
    "caregiving",
    "caretaker",
    "nurse",
    "support",
    "assistance",
    "help",
    "aid",
    "home care",
    "hospice",
    "palliative",
    "rehab",
    "recovery",

    # --------------------------------------------------------
    # Prevention
    # --------------------------------------------------------

    "prevention",
    "prevent",
    "avoid",
    "risk",
    "safety",
    "hygiene",
    "wash hands",
    "mask",
    "sanitize",
    "quarantine",
    "isolation",
    "social distancing",

    # --------------------------------------------------------
    # Additional Diseases
    # --------------------------------------------------------

    "monkeypox",
    "hand foot mouth",
    "kawasaki",
    "scarlet fever",
    "gastritis",
    "ulcer",
    "ibs",
    "crohn",
    "colitis",
    "kidney stone",
    "uti",
    "urinary",
    "eczema",
    "psoriasis",
    "acne",
    "skin cancer",
    "melanoma",
    "thyroid",
    "hyperthyroid",
    "hypothyroid",
    "goiter",
    "anemia",
    "hemophilia",
    "leukemia",
    "lymphoma",
    "glaucoma",
    "cataract",
    "conjunctivitis",
    "meningitis",
    "encephalitis",
    "sepsis",
    "stroke",
    "heart attack",
    "cardiac",
    "angina"
]


# ============================================================
# HEALTH FILTER
# ============================================================

def is_health_related(query):

    query_lower = query.lower()

    for keyword in HEALTH_KEYWORDS:

        if keyword in query_lower:

            return True

    return False


# ============================================================
# SHORT-TERM MEMORY
# ============================================================

def format_conversation_history(
    conversation_history
):

    """
    Convert previous conversation messages
    into readable text for Gemini.
    """

    if not conversation_history:

        return (
            "No previous conversation. "
            "This is the first message."
        )

    history_lines = []

    for message in conversation_history:

        role = message.get(
            "role",
            "user"
        )

        content = message.get(
            "content",
            ""
        )

        if not content:

            continue

        if role == "user":

            speaker = "USER"

        elif role == "assistant":

            speaker = "ASSISTANT"

        else:

            speaker = role.upper()

        history_lines.append(
            f"{speaker}: {content}"
        )

    if not history_lines:

        return (
            "No previous conversation. "
            "This is the first message."
        )

    return "\n".join(history_lines)


# ============================================================
# RETRY FUNCTION
# ============================================================

def run_gemini_with_retry(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None,
    max_retries=3
):

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
                f"❌ Gemini attempt "
                f"{attempt + 1}/{max_retries} failed: {e}"
            )

            if attempt == max_retries - 1:

                return f"""
⚠️ Sorry, I couldn't process your request.

Error: {str(e)}

Please try:
1. Refreshing the page
2. Checking your Gemini API key
3. Checking your internet connection
4. Rephrasing your question
"""

            # Wait before retry
            time.sleep(
                2 ** attempt
            )

    return "Unable to process your request."


# ============================================================
# MAIN GEMINI FUNCTION
# ============================================================

def run_gemini(
    user_input,
    age_group="All Ages",
    language="English",
    conversation_history=None
):

    try:

        # ----------------------------------------------------
        # MAKE SURE HISTORY EXISTS
        # ----------------------------------------------------

        if conversation_history is None:

            conversation_history = []

        # ----------------------------------------------------
        # FORMAT HISTORY
        # ----------------------------------------------------

        history_text = format_conversation_history(
            conversation_history
        )

        # ----------------------------------------------------
        # CHECK CACHE
        # ----------------------------------------------------

        cached_response = cache.get(
            user_input,
            age_group,
            language,
            conversation_history
        )

        if cached_response:

            print(
                "✅ Using cached response"
            )

            return cached_response

        # ----------------------------------------------------
        # HEALTH FILTER
        # ----------------------------------------------------

        if not is_health_related(
            user_input
        ):

            return f"""
I'm a Health Education Assistant focused on
providing information about symptoms, diseases,
and health conditions.

Your question:

"{user_input}"

Please ask a health-related question such as:

• What is diabetes?
• What are the symptoms of high blood pressure?
• What is arthritis?
• What is food poisoning?
• What is dizziness?
• What causes headaches?
• What are prevention tips for flu?

⚠️ Educational information only.
Please consult a qualified healthcare professional
for medical advice.
"""

        # ----------------------------------------------------
        # LANGUAGE
        # ----------------------------------------------------

        language_instructions = {

            "English":
                "Respond in English.",

            "Urdu":
                "Respond in Urdu using Urdu script (اردو).",

            "Hindi":
                "Respond in Hindi using Devanagari script (हिंदी).",

            "Spanish":
                "Respond in Spanish.",

            "French":
                "Respond in French.",

            "Arabic":
                "Respond in Arabic using Arabic script (العربية)."
        }

        lang_instruction = language_instructions.get(
            language,
            "Respond in English."
        )

        # ----------------------------------------------------
        # SYSTEM INSTRUCTION
        # ----------------------------------------------------

        system_instruction = f"""
You are a Health Education Assistant.

Your role is to provide clear, safe,
educational health information.

You are NOT a doctor.

You must not diagnose a user.

You must not claim certainty about a
user's medical condition.

You must not replace professional
medical advice.

Use the conversation history to understand
follow-up questions.

If the user says things such as:

"it"
"its"
"they"
"that"
"the symptoms"
"what about this?"

use the previous conversation to understand
what they are referring to.

Do not invent information that is not present
in the conversation.

TARGET AGE GROUP:
{age_group}

LANGUAGE:
{language}

LANGUAGE INSTRUCTION:
{lang_instruction}

Always keep the response educational,
clear, and appropriate for the selected
age group.

For urgent or potentially serious symptoms,
recommend seeking appropriate professional
medical care.

Do not provide a diagnosis.

Do not present your response as personalized
medical treatment.

Include an educational disclaimer when
appropriate.
"""

        # ----------------------------------------------------
        # USER PROMPT
        # ----------------------------------------------------

        prompt = f"""
PREVIOUS CONVERSATION:

----------------------------------------
{history_text}
----------------------------------------

CURRENT USER QUESTION:

{user_input}

Please answer the current question using
the previous conversation when relevant.

If this is a follow-up question, do not ask
the user to repeat information that is already
available in the conversation.

Provide useful educational information.

When appropriate, organize the response using:

## 📋 Overview

## 🔍 How This Affects {age_group}

## ⚠️ Signs to Watch For

## 🏠 Self-Care Information

## 🚨 When to Seek Medical Care

## 💡 Prevention Tips

Do not force every section if it is not relevant.

Remember:

This is educational information only.
It is not a diagnosis, personalized treatment,
or replacement for professional medical care.
"""

        # ----------------------------------------------------
        # SEND REQUEST
        # ----------------------------------------------------

        print(
            "Sending request to Gemini..."
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={
                "system_instruction":
                    system_instruction,
                "temperature": 0.4,
                "max_output_tokens": 1200
            }
        )

        # ----------------------------------------------------
        # GET RESPONSE TEXT
        # ----------------------------------------------------

        result = response.text

        if not result:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        # ----------------------------------------------------
        # SAVE CACHE
        # ----------------------------------------------------

        cache.set(
            user_input,
            age_group,
            language,
            result,
            conversation_history
        )

        print(
            "✅ Response received!"
        )

        return result

    except Exception as e:

        raise RuntimeError(
            f"Gemini API error: {str(e)}"
        ) from e