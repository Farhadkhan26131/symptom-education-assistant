
"""
AI Health Education Assistant

=============================

Streamlit application layer.

Architecture:

User
  ↓
Streamlit UI
  ↓
Persistent Session Layer
  ↓
Short-Term Memory + Compact Summary
  ↓
Intent / Agent Routing
  ↓
Optional Local Health Tool
  ↓
Gemini Primary
  ↓
Groq Fallback
  ↓
Persistent Session + Analytics

This application provides general health education only.

It is NOT a diagnostic or treatment system.
"""

import streamlit as st
import time
import random
import re
from datetime import datetime

# ============================================================
# AGENT IMPORT
# ============================================================

from agent import HealthAgent

# ============================================================
# DIRECT GEMINI LAYER
# ============================================================

try:
    from gemini_agent import run_gemini_with_retry
except ImportError:
    run_gemini_with_retry = None

# ============================================================
# DATABASE IMPORT
# ============================================================

from database import ChatDatabase

# ============================================================
# SESSION MANAGER IMPORT
# ============================================================

from session_manager import SessionManager

# ============================================================
# OPTIONAL ANALYTICS IMPORT
# ============================================================

try:
    from analytics_dashboard import show_analytics
except ImportError:
    try:
        from analytics_dashboard import show_analytics_dashboard

        def show_analytics():
            show_analytics_dashboard(db)

    except ImportError:
        show_analytics = None

# ============================================================
# OPTIONAL VOICE INPUT
# ============================================================

try:
    from voice_input import get_voice_input
except ImportError:
    get_voice_input = None

# ============================================================
# OPTIONAL PDF EXPORT
# ============================================================

try:
    from pdf_export import create_pdf
except ImportError:
    create_pdf = None

try:
    from pdf_export import generate_health_report
except ImportError:
    generate_health_report = None

# ============================================================
# OPTIONAL LOCAL HEALTH TOOL
# ============================================================

try:
    from tools import search_symptom_information
except ImportError:
    search_symptom_information = None

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CONFIGURATION
# ============================================================

MAX_CONTEXT_MESSAGES = 12
SESSION_TTL_HOURS = 24

SUMMARY_TRIGGER = MAX_CONTEXT_MESSAGES + 6
MAX_SUMMARY_ITEMS = 6
MAX_TOOL_CONTEXT_CHARS = 1200

# ============================================================
# DATABASE
# ============================================================

db = ChatDatabase()

# ============================================================
# HEALTH AGENT
# ============================================================

health_agent = HealthAgent()

# ============================================================
# SESSION MANAGER
# ============================================================

session_manager = SessionManager(
    sessions_dir="sessions",
    ttl_hours=SESSION_TTL_HOURS
)

# ============================================================
# DEFAULT ASSISTANT GREETING
# ============================================================

DEFAULT_GREETING = {
    "role": "assistant",
    "content": (
        "👋 Hello! I'm your Health Assistant. "
        "I can provide general educational information about "
        "symptoms, prevention, self-care, and healthy habits. "
        "Please remember that I am not a doctor and cannot "
        "diagnose or treat medical conditions."
    )
}

# ============================================================
# RATE LIMITER
# ============================================================

rate_limit_data = {}

MAX_REQUESTS = 20
TIME_WINDOW = 60


def check_rate_limit(user_id):
    """
    Allow a maximum number of requests within a time window.
    """

    current_time = time.time()

    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = []

    rate_limit_data[user_id] = [
        request_time
        for request_time in rate_limit_data[user_id]
        if current_time - request_time < TIME_WINDOW
    ]

    if len(rate_limit_data[user_id]) >= MAX_REQUESTS:
        return False

    rate_limit_data[user_id].append(current_time)

    return True


# ============================================================
# CLEAN AI RESPONSE
# ============================================================

def clean_ai_response(text):
    """
    Clean accidental HTML and formatting artifacts
    from AI-generated responses.
    """

    if not text:
        return ""

    text = str(text)

    # Remove SVG / anchor artifacts.
    text = re.sub(
        r"\[?\s*svg\s*\]?\([^)]*\)",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove accidental Health Assistant HTML wrapper.
    text = re.sub(
        r"<strong>\s*[/\\*]*\s*🩺\s*Health Assistant\s*[/\\*]*\s*</strong>",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Convert <br> tags to new lines.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    # Remove div tags.
    text = re.sub(
        r"</?div[^>]*>",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove markdown code fences.
    text = re.sub(
        r"```(?:html)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```",
        "",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{4,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# FOLLOW-UP + SYMPTOM QUESTION PREPARATION
# ============================================================

def prepare_health_question(user_input, conversation_history):
    """
    Prepare the user's question before sending it to Gemini/Groq.

    Handles:

    1. Follow-up questions:
       "What is a headache?"
       "What are its common causes?"

    2. Symptom questions:
       "I feel dizzy, what does it mean?"

    This does not diagnose the user.
    It only provides context to the AI.
    """

    if not user_input:
        return user_input

    text = str(user_input).strip()

    if not text:
        return text

    lower_text = text.lower()

    # ========================================================
    # FIND PREVIOUS USER QUESTION
    # ========================================================

    previous_user_question = None

    for message in reversed(conversation_history or []):
        if message.get("role") == "user":
            previous_user_question = message.get("content")
            break

    # ========================================================
    # FOLLOW-UP DETECTION
    # ========================================================

    follow_up_patterns = [
        "its ",
        "it's ",
        "it ",
        "this ",
        "that ",
        "these ",
        "those ",
        "their ",
        "what are its",
        "what is its",
        "what are its common causes",
        "what causes it",
        "what are the causes",
        "common causes",
        "more about it",
        "tell me more",
        "what about it",
        "how about it"
    ]

    is_follow_up = any(
        pattern in lower_text
        for pattern in follow_up_patterns
    )

    if is_follow_up and previous_user_question:

        return f"""
FOLLOW-UP HEALTH QUESTION CONTEXT

Previous user question:
"{previous_user_question}"

Current user question:
"{text}"

The current question is a follow-up to the previous health topic.

Resolve words such as:
- it
- its
- this
- that
- these
- those
- their

using the health topic from the previous question.

For example:
If the previous question is about "headache" and the current
question says "What are its common causes?", understand "its"
as referring to "headache".

Answer the current question directly and naturally.

Do not mention this instruction.
Do not mention that you are resolving context.
Do not say that the user needs to ask another question.

CURRENT QUESTION:
{text}
"""

    # ========================================================
    # SYMPTOM DETECTION
    # ========================================================

    symptom_words = [
        "dizzy",
        "dizziness",
        "vertigo",
        "headache",
        "head pain",
        "stomach pain",
        "stomach ache",
        "back pain",
        "joint pain",
        "itching",
        "sore throat",
        "cough",
        "fever",
        "nausea",
        "vomiting",
        "fatigue",
        "weakness",
        "shortness of breath",
        "rash",
        "swelling",
        "pain"
    ]

    has_symptom = any(
        symptom in lower_text
        for symptom in symptom_words
    )

    if has_symptom:

        return f"""
HEALTH SYMPTOM QUESTION

The user is asking about a health symptom.

User question:
"{text}"

Treat this as a valid health education question.

Provide simple, general educational information.

Explain possible common meanings or causes without diagnosing
the user.

Include appropriate safety guidance.

If symptoms are severe, sudden, worsening, or concerning,
recommend seeking professional medical care.

Do not diagnose the user.
Do not prescribe medication.
Do not provide medication doses.

Answer the user's question directly.

USER QUESTION:
{text}
"""

    # ========================================================
    # NORMAL QUESTION
    # ========================================================

    return text


# ============================================================
# SESSION INITIALIZATION
# ============================================================

def initialize_session():
    """
    Create or restore the persistent SessionManager session.
    """

    # --------------------------------------------------------
    # Restore existing session
    # --------------------------------------------------------

    if "session_id" in st.session_state:

        existing_session_id = st.session_state.session_id

        saved_session = session_manager.load_session(
            existing_session_id
        )

        if saved_session is not None:

            state = saved_session.get("state", {})

            st.session_state.messages = state.get(
                "history",
                [DEFAULT_GREETING.copy()]
            )

            st.session_state.summary = state.get(
                "summary",
                ""
            )

            st.session_state.scratchpad = state.get(
                "scratchpad",
                {}
            )

            st.session_state.last_tool_result = state.get(
                "last_tool_result",
                None
            )

            st.session_state.plan_step = state.get(
                "plan_step",
                0
            )

            st.session_state.turn_state = state.get(
                "turn_state",
                {}
            )

            preferences = state.get(
                "preferences",
                {}
            )

            st.session_state.age_group = preferences.get(
                "age_group",
                "Adults"
            )

            st.session_state.language = preferences.get(
                "language",
                "English"
            )

            st.session_state.theme = preferences.get(
                "theme",
                "Dark"
            )

            st.session_state.query_count = state.get(
                "query_count",
                0
            )

            return

        st.session_state.pop(
            "session_id",
            None
        )

    # ========================================================
    # CREATE NEW SESSION
    # ========================================================

    initial_state = {
        "history": [
            DEFAULT_GREETING.copy()
        ],
        "summary": "",
        "scratchpad": {},
        "last_tool_result": None,
        "plan_step": 0,
        "turn_state": {},
        "preferences": {
            "age_group": "Adults",
            "language": "English",
            "theme": "Dark"
        },
        "query_count": 0
    }

    new_session = session_manager.create_session(
        initial_state=initial_state
    )

    st.session_state.session_id = new_session["session_id"]

    st.session_state.messages = initial_state["history"]
    st.session_state.summary = initial_state["summary"]
    st.session_state.scratchpad = initial_state["scratchpad"]
    st.session_state.last_tool_result = initial_state["last_tool_result"]
    st.session_state.plan_step = initial_state["plan_step"]
    st.session_state.turn_state = initial_state["turn_state"]

    st.session_state.age_group = "Adults"
    st.session_state.language = "English"
    st.session_state.theme = "Dark"
    st.session_state.query_count = 0


# ============================================================
# INITIALIZE SESSION
# ============================================================

initialize_session()

# ============================================================
# OTHER STREAMLIT SESSION STATE
# ============================================================

if "quick_topic" not in st.session_state:
    st.session_state.quick_topic = None

if "process_quick_topic" not in st.session_state:
    st.session_state.process_quick_topic = False

if "user_id" not in st.session_state:
    st.session_state.user_id = str(
        random.randint(1000, 9999)
    )

if "current_page" not in st.session_state:
    st.session_state.current_page = "Health Assistant"

if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""


# ============================================================
# SAVE CURRENT SESSION
# ============================================================

def save_current_session():
    """
    Save application state to persistent JSON.
    """

    state = {
        "history": st.session_state.messages,
        "summary": st.session_state.get(
            "summary",
            ""
        ),
        "scratchpad": st.session_state.get(
            "scratchpad",
            {}
        ),
        "last_tool_result": st.session_state.get(
            "last_tool_result",
            None
        ),
        "plan_step": st.session_state.get(
            "plan_step",
            0
        ),
        "turn_state": st.session_state.get(
            "turn_state",
            {}
        ),
        "preferences": {
            "age_group": st.session_state.age_group,
            "language": st.session_state.language,
            "theme": st.session_state.theme
        },
        "query_count": st.session_state.query_count
    }

    try:

        session_manager.save_session(
            st.session_state.session_id,
            state
        )

        return True

    except Exception as e:

        print(
            f"⚠️ Session save failed: {e}"
        )

        return False


# ============================================================
# COMPACT MEMORY SUMMARY
# ============================================================

def build_memory_summary():
    """
    Build a small deterministic summary from older conversation.

    This is NOT chain-of-thought.
    Only simple application-level memory is stored.
    """

    messages = st.session_state.messages

    if len(messages) <= SUMMARY_TRIGGER:

        return st.session_state.get(
            "summary",
            ""
        )

    older_messages = messages[
        1:-MAX_CONTEXT_MESSAGES
    ]

    user_topics = []

    for message in older_messages:

        if message.get("role") != "user":
            continue

        content = str(
            message.get("content", "")
        ).strip()

        if not content:
            continue

        short_text = re.split(
            r"[.!?\n]",
            content
        )[0].strip()

        if len(short_text) > 140:

            short_text = (
                short_text[:137] + "..."
            )

        if (
            short_text
            and short_text not in user_topics
        ):

            user_topics.append(
                short_text
            )

    user_topics = user_topics[
        -MAX_SUMMARY_ITEMS:
    ]

    if not user_topics:

        return st.session_state.get(
            "summary",
            ""
        )

    summary = (
        "Earlier conversation topics: "
        + "; ".join(user_topics)
        + "."
    )

    return summary[:1000]


# ============================================================
# SHORT-TERM MEMORY / CONTEXT WINDOW
# ============================================================

def get_conversation_history():
    """
    Return recent conversation messages.

    IMPORTANT:
    The current user message is already appended to messages,
    therefore we remove the last message before sending history.
    """

    if len(st.session_state.messages) <= 1:
        return []

    previous_messages = (
        st.session_state.messages[:-1]
    )

    return previous_messages[
        -MAX_CONTEXT_MESSAGES:
    ]


# ============================================================
# AGENT ROUTING LABEL
# ============================================================

def get_agent_label(intent):

    labels = {

        "emergency":
            "Emergency Safety Agent",

        "symptom_education":
            "Symptom Education Agent",

        "prevention":
            "Prevention Agent",

        "lifestyle":
            "Lifestyle Agent",

        "general_health":
            "General Health Agent"
    }

    return labels.get(
        intent,
        "General Health Agent"
    )


# ============================================================
# LOCAL TOOL TOPIC EXTRACTION
# ============================================================

def extract_tool_topic(prompt):

    if not prompt:
        return None

    text = str(prompt).lower()

    known_topics = [

        "diabetes",
        "headache",
        "fever",
        "cough",
        "cold",
        "flu",
        "dizziness",
        "dizzy",
        "nausea",
        "vomiting",
        "diarrhea",
        "fatigue",
        "weakness",
        "rash",
        "swelling",
        "pain"
    ]

    for topic in known_topics:

        if topic in text:
            return topic

    return None


# ============================================================
# RUN LOCAL HEALTH TOOL
# ============================================================

def run_local_health_tool(
    topic,
    age_group
):

    if not topic:
        return None

    if search_symptom_information is None:
        return None

    try:

        result = search_symptom_information(
            symptom=topic,
            age_group=age_group
        )

        if result:

            return str(result)[
                :MAX_TOOL_CONTEXT_CHARS
            ]

    except Exception as e:

        print(
            f"⚠️ Local health tool failed: {e}"
        )

    return None


# ============================================================
# EMERGENCY SAFETY PREFIX
# ============================================================

def build_emergency_prompt(prompt):

    emergency_prefix = """

IMPORTANT SAFETY NOTICE:

The user's message may describe a potentially serious
or emergency medical situation.

The response must clearly recommend seeking urgent
professional medical evaluation.

Do not attempt to diagnose the condition.

Do not provide false reassurance.

If symptoms are severe, worsening, or potentially
life-threatening, advise the user to contact local
emergency services or go to the nearest emergency
medical facility immediately.

Do not provide medication doses.

USER QUESTION:

"""

    return emergency_prefix + prompt


# ============================================================
# UNIFIED MESSAGE PROCESSOR
# ============================================================

def process_user_message(prompt):

    """
    Central processing function.

    Flow:

    1. Validate input
    2. Rate-limit
    3. Add user message
    4. Detect intent
    5. Route to logical agent
    6. Run optional local tool
    7. Build short-term memory
    8. Resolve follow-up question
    9. Call Gemini with Groq fallback
    10. Save response
    11. Update memory
    12. Update turn state
    13. Log analytics
    14. Save persistent session
    """

    if not prompt:
        return

    prompt = str(prompt).strip()

    if not prompt:
        return

    # ========================================================
    # RATE LIMIT
    # ========================================================

    if not check_rate_limit(
        st.session_state.user_id
    ):

        st.warning(
            "You have reached the temporary request limit. "
            "Please wait a moment and try again."
        )

        return

    # ========================================================
    # ADD USER MESSAGE
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    # ========================================================
    # INTENT DETECTION
    # ========================================================

    try:

        intent = health_agent.detect_intent(
            prompt
        )

    except Exception:

        intent = "general_health"

    # ========================================================
    # AGENT ROUTING
    # ========================================================

    active_agent = get_agent_label(
        intent
    )

    # ========================================================
    # LOCAL HEALTH TOOL
    # ========================================================

    tool_topic = None
    tool_result = None

    if intent != "emergency":

        tool_topic = extract_tool_topic(
            prompt
        )

        if tool_topic:

            tool_result = run_local_health_tool(
                topic=tool_topic,
                age_group=st.session_state.age_group
            )

    st.session_state.last_tool_result = (
        tool_result
    )

    # ========================================================
    # PLAN STEP
    # ========================================================

    st.session_state.plan_step += 1

    current_plan_step = (
        st.session_state.plan_step
    )

    # ========================================================
    # PROCESSING TURN STATE
    # ========================================================

    st.session_state.turn_state = {

        "status":
            "processing",

        "plan_step":
            current_plan_step,

        "query_count":
            st.session_state.query_count + 1,

        "intent":
            intent,

        "active_agent":
            active_agent,

        "tool_used":
            bool(tool_result),

        "tool_topic":
            tool_topic,

        "started_at":
            datetime.now().isoformat()
    }

    # ========================================================
    # STRUCTURED SCRATCHPAD
    # ========================================================

    st.session_state.scratchpad = {

        "last_query":
            prompt,

        "intent":
            intent,

        "active_agent":
            active_agent,

        "tool_used":
            bool(tool_result),

        "tool_topic":
            tool_topic,

        "plan_step":
            current_plan_step,

        "status":
            "processing"
    }

    # ========================================================
    # MEMORY SUMMARY
    # ========================================================

    current_summary = (
        st.session_state.get(
            "summary",
            ""
        )
    )

    if len(st.session_state.messages) > SUMMARY_TRIGGER:

        current_summary = build_memory_summary()

        st.session_state.summary = (
            current_summary
        )

    # ========================================================
    # SHORT-TERM CONTEXT
    # ========================================================

    conversation_history = (
        get_conversation_history()
    )

    # ========================================================
    # PREPARE AI QUESTION
    # ========================================================

    ai_prompt = prepare_health_question(
        prompt,
        conversation_history
    )

    # ========================================================
    # EMERGENCY SAFETY
    # ========================================================

    if intent == "emergency":

        ai_prompt = build_emergency_prompt(
            ai_prompt
        )

    # ========================================================
    # AI PROCESSING
    # ========================================================

    response = ""

    with st.spinner("🧠 Thinking..."):

        try:

            # ------------------------------------------------
            # PRIMARY ARCHITECTURE
            # ------------------------------------------------

            if run_gemini_with_retry is not None:

                result = run_gemini_with_retry(

                    user_input=ai_prompt,

                    age_group=
                        st.session_state.age_group,

                    language=
                        st.session_state.language,

                    conversation_history=
                        conversation_history,

                    summary=
                        current_summary,

                    tool_result=
                        tool_result
                )

            else:

                # Compatibility fallback.

                result = health_agent.run(

                    user_input=ai_prompt,

                    age_group=
                        st.session_state.age_group,

                    language=
                        st.session_state.language,

                    conversation_history=
                        conversation_history
                )

            # ------------------------------------------------
            # SUPPORT STRING OR DICT RESPONSE
            # ------------------------------------------------

            if isinstance(result, dict):

                response = result.get(
                    "response",
                    ""
                )

                returned_intent = result.get(
                    "intent"
                )

                returned_agent = result.get(
                    "active_agent"
                )

                if returned_intent:

                    intent = returned_intent

                if returned_agent:

                    active_agent = returned_agent

            else:

                response = result

            # ------------------------------------------------
            # CLEAN RESPONSE
            # ------------------------------------------------

            response = clean_ai_response(
                response
            )

            if not response:

                response = (
                    "I could not generate a response "
                    "right now. Please try again."
                )

        except Exception as e:

            print(
                f"❌ AI processing error: {e}"
            )

            response = (
                "Sorry, I couldn't process your request "
                "right now. Please try again later."
            )

            # ------------------------------------------------
            # SAVE ERROR STATE
            # ------------------------------------------------

            st.session_state.turn_state = {

                "status":
                    "error",

                "plan_step":
                    current_plan_step,

                "query_count":
                    st.session_state.query_count,

                "intent":
                    intent,

                "active_agent":
                    active_agent,

                "tool_used":
                    bool(tool_result),

                "tool_topic":
                    tool_topic,

                "error":
                    True,

                "completed_at":
                    datetime.now().isoformat()
            }

            st.session_state.scratchpad = {

                "last_query":
                    prompt,

                "intent":
                    intent,

                "active_agent":
                    active_agent,

                "tool_used":
                    bool(tool_result),

                "tool_topic":
                    tool_topic,

                "status":
                    "error",

                "plan_step":
                    current_plan_step
            }

            save_current_session()

    # ========================================================
    # ADD ASSISTANT RESPONSE
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )

    # ========================================================
    # UPDATE QUERY COUNT
    # ========================================================

    st.session_state.query_count += 1

    # ========================================================
    # UPDATE MEMORY SUMMARY
    # ========================================================

    if len(st.session_state.messages) > SUMMARY_TRIGGER:

        st.session_state.summary = (
            build_memory_summary()
        )

    # ========================================================
    # COMPLETED TURN STATE
    # ========================================================

    st.session_state.turn_state = {

        "status":
            "completed",

        "plan_step":
            current_plan_step,

        "query_count":
            st.session_state.query_count,

        "intent":
            intent,

        "active_agent":
            active_agent,

        "tool_used":
            bool(tool_result),

        "tool_topic":
            tool_topic,

        "response_available":
            bool(response),

        "completed_at":
            datetime.now().isoformat()
    }

    # ========================================================
    # COMPLETED SCRATCHPAD
    # ========================================================

    st.session_state.scratchpad = {

        "last_query":
            prompt,

        "intent":
            intent,

        "active_agent":
            active_agent,

        "tool_used":
            bool(tool_result),

        "tool_topic":
            tool_topic,

        "last_response_available":
            bool(response),

        "plan_step":
            current_plan_step,

        "status":
            "completed"
    }

    # ========================================================
    # DATABASE LOGGING
    # ========================================================

    try:

        db.add_conversation(

            st.session_state.user_id,

            st.session_state.messages,

            st.session_state.age_group,

            st.session_state.language,

            1
        )

    except Exception as e:

        print(
            f"⚠️ Database logging failed: {e}"
        )

    # ========================================================
    # SAVE PERSISTENT SESSION
    # ========================================================

    save_current_session()


# ============================================================
# DARK THEME
# ============================================================

if st.session_state.theme == "Dark":

    st.markdown(
        """
        <style>

        .stApp {
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }

        .main {
            background-color: #0f172a !important;
        }

        [data-testid="stSidebar"] {
            background-color: #111827 !important;
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        .main-title {
            font-size: 42px;
            font-weight: 800;
            color: #38bdf8;
            margin-bottom: 5px;
        }

        .subtitle {
            font-size: 18px;
            color: #94a3b8;
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 28px;
            font-weight: 700;
            color: #38bdf8;
            margin-top: 20px;
            margin-bottom: 15px;
        }

        .info-card {
            padding: 20px;
            border-radius: 15px;
            background-color: #1e293b;
            border: 1px solid #334155;
            margin-bottom: 15px;
            color: #f8fafc;
        }

        .info-card h3 {
            color: #38bdf8 !important;
        }

        .info-card p {
            color: #cbd5e1 !important;
        }

        [data-testid="stChatMessage"] {
            background-color: #1e293b !important;
            border: 1px solid #334155 !important;
            border-radius: 16px !important;
            padding: 16px !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div {
            color: #f8fafc !important;
        }

        [data-testid="stChatMessage"] h1,
        [data-testid="stChatMessage"] h2,
        [data-testid="stChatMessage"] h3,
        [data-testid="stChatMessage"] h4 {
            color: #38bdf8 !important;
        }

        [data-testid="stChatMessage"] strong {
            color: #f8fafc !important;
        }

        [data-testid="stChatMessage"] a {
            color: #7dd3fc !important;
        }

        [data-testid="stChatInput"] {
            background-color: #1e293b !important;
            border: 1px solid #475569 !important;
            border-radius: 14px !important;
        }

        [data-testid="stChatInput"] textarea {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            caret-color: #38bdf8 !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #94a3b8 !important;
        }

        .stMarkdown {
            color: #f8fafc;
        }

        .disclaimer {
            background-color: #3f2f14;
            border: 1px solid #854d0e;
            padding: 15px;
            border-radius: 10px;
            color: #fef3c7;
            margin-top: 20px;
        }

        footer {
            visibility: hidden;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# LIGHT THEME
# ============================================================

else:

    st.markdown(
        """
        <style>

        .stApp {
            background-color: #f8fafc !important;
            color: #0f172a !important;
        }

        .main {
            background-color: #f8fafc !important;
        }

        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
        }

        [data-testid="stSidebar"] * {
            color: #0f172a !important;
        }

        .main-title {
            font-size: 42px;
            font-weight: 800;
            color: #0284c7;
            margin-bottom: 5px;
        }

        .subtitle {
            font-size: 18px;
            color: #475569;
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 28px;
            font-weight: 700;
            color: #0284c7;
            margin-top: 20px;
            margin-bottom: 15px;
        }

        .info-card {
            padding: 20px;
            border-radius: 15px;
            background-color: white;
            border: 1px solid #e2e8f0;
            margin-bottom: 15px;
        }

        [data-testid="stChatMessage"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 16px !important;
            padding: 16px !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div {
            color: #0f172a !important;
        }

        [data-testid="stChatMessage"] h1,
        [data-testid="stChatMessage"] h2,
        [data-testid="stChatMessage"] h3,
        [data-testid="stChatMessage"] h4 {
            color: #0284c7 !important;
        }

        [data-testid="stChatInput"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 14px !important;
        }

        [data-testid="stChatInput"] textarea {
            background-color: #ffffff !important;
            color: #0f172a !important;
            caret-color: #0284c7 !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #64748b !important;
        }

        .disclaimer {
            background-color: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 15px;
            border-radius: 10px;
            color: #78350f;
            margin-top: 20px;
        }

        footer {
            visibility: hidden;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🩺 Health Assistant</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Educational health information powered by AI'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🩺 Health Assistant"
    )

    st.markdown("---")

    # ========================================================
    # NAVIGATION
    # ========================================================

    page = st.radio(
        "Navigation",
        [
            "Health Assistant",
            "Health Tips",
            "Analytics",
            "Contact"
        ],
        index=[
            "Health Assistant",
            "Health Tips",
            "Analytics",
            "Contact"
        ].index(
            st.session_state.current_page
        )
    )

    st.session_state.current_page = page

    st.markdown("---")

    # ========================================================
    # SETTINGS
    # ========================================================

    st.markdown(
        "### ⚙️ Settings"
    )

    st.session_state.theme = st.selectbox(
        "Theme",
        [
            "Dark",
            "Light"
        ],
        index=[
            "Dark",
            "Light"
        ].index(
            st.session_state.theme
        )
    )

    st.session_state.language = st.selectbox(
        "Language",
        [
            "English",
            "Urdu",
            "Hindi",
            "Arabic"
        ],
        index=[
            "English",
            "Urdu",
            "Hindi",
            "Arabic"
        ].index(
            st.session_state.language
        )
    )

    st.session_state.age_group = st.selectbox(
        "Age Group",
        [
            "Children",
            "Teenagers",
            "Adults",
            "Older Adults"
        ],
        index=[
            "Children",
            "Teenagers",
            "Adults",
            "Older Adults"
        ].index(
            st.session_state.age_group
        )
    )

    save_current_session()

    st.markdown("---")

    # ========================================================
    # HEALTH CATEGORIES
    # ========================================================

    st.markdown(
        "### 🏥 Health Categories"
    )

    disease_categories = {

        "🤒 Common Symptoms": [
            "Headache",
            "Fever",
            "Cough",
            "Cold",
            "Fatigue"
        ],

        "🫀 Chronic Conditions": [
            "Diabetes",
            "High Blood Pressure",
            "Heart Health"
        ],

        "🧠 Mental Wellness": [
            "Stress",
            "Anxiety",
            "Sleep"
        ],

        "🥗 Healthy Lifestyle": [
            "Nutrition",
            "Exercise",
            "Hydration"
        ]
    }

    selected_category = st.selectbox(
        "Select Category",
        list(
            disease_categories.keys()
        )
    )

    selected_topic = st.selectbox(
        "Select Topic",
        disease_categories[
            selected_category
        ]
    )

    if st.button(
        "Learn About Topic",
        use_container_width=True
    ):

        st.session_state.quick_topic = (
            selected_topic
        )

        st.session_state.process_quick_topic = True

        st.rerun()

    st.markdown("---")

    # ========================================================
    # ACTIONS
    # ========================================================

    st.markdown(
        "### 🛠️ Actions"
    )

    # ========================================================
    # CLEAR OLD CHATS
    # ========================================================

    if st.button(
        "🗑️ Clear Old Chats",
        use_container_width=True
    ):

        st.session_state.messages = [
            DEFAULT_GREETING.copy()
        ]

        st.session_state.summary = ""
        st.session_state.scratchpad = {}
        st.session_state.last_tool_result = None
        st.session_state.plan_step = 0
        st.session_state.turn_state = {}
        st.session_state.query_count = 0
        st.session_state.quick_topic = None
        st.session_state.process_quick_topic = False

        save_current_session()

        st.success(
            "Conversation history cleared."
        )

        st.rerun()

    # ========================================================
    # RESET EVERYTHING
    # ========================================================

    if st.button(
        "🔄 Reset Everything",
        use_container_width=True
    ):

        try:

            session_manager.delete_session(
                st.session_state.session_id
            )

        except Exception:
            pass

        for key in list(
            st.session_state.keys()
        ):
            del st.session_state[key]

        st.rerun()

    st.markdown("---")

    # ========================================================
    # PDF EXPORT
    # ========================================================

    st.markdown(
        "### 📄 Export"
    )

    if st.button(
        "Export Conversation",
        use_container_width=True
    ):

        pdf_file = None

        # ----------------------------------------------------
        # Method 1: create_pdf(messages)
        # ----------------------------------------------------

        if create_pdf is not None:

            try:

                pdf_file = create_pdf(
                    st.session_state.messages
                )

            except Exception as e:

                st.error(
                    f"PDF export failed: {str(e)}"
                )

        # ----------------------------------------------------
        # Method 2: generate_health_report(...)
        # ----------------------------------------------------

        elif generate_health_report is not None:

            try:

                last_user = ""
                last_assistant = ""

                for message in reversed(
                    st.session_state.messages
                ):

                    if (
                        not last_assistant
                        and message.get("role")
                        == "assistant"
                    ):

                        last_assistant = message.get(
                            "content",
                            ""
                        )

                    elif (
                        not last_user
                        and message.get("role")
                        == "user"
                    ):

                        last_user = message.get(
                            "content",
                            ""
                        )

                    if (
                        last_user
                        and last_assistant
                    ):
                        break

                if not last_user or not last_assistant:

                    st.warning(
                        "There is no completed conversation "
                        "available to export yet."
                    )

                else:

                    pdf_file = generate_health_report(
                        last_user,
                        last_assistant,
                        st.session_state.age_group,
                        st.session_state.language
                    )

            except Exception as e:

                st.error(
                    f"PDF export failed: {str(e)}"
                )

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        if pdf_file:

            try:

                with open(
                    pdf_file,
                    "rb"
                ) as file:

                    st.download_button(
                        label="⬇️ Download PDF",
                        data=file,
                        file_name="health_conversation.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            except Exception as e:

                st.error(
                    f"Unable to read PDF file: {str(e)}"
                )

        elif (
            create_pdf is None
            and generate_health_report is None
        ):

            st.warning(
                "PDF export module is not available."
            )

    st.markdown("---")

    # ========================================================
    # SESSION INFORMATION
    # ========================================================

    st.markdown(
        "### 💾 Session"
    )

    st.caption(
        f"Session ID: "
        f"{st.session_state.session_id}"
    )

    st.caption(
        f"Questions: "
        f"{st.session_state.query_count}"
    )

    st.caption(
        f"Context window: "
        f"{MAX_CONTEXT_MESSAGES} messages"
    )

    st.caption(
        f"Memory summary: "
        f"{'Available' if st.session_state.get('summary') else 'Not needed yet'}"
    )

    if st.session_state.get(
        "turn_state"
    ):

        current_agent = (
            st.session_state.turn_state.get(
                "active_agent"
            )
        )

        if current_agent:

            st.caption(
                f"Active route: {current_agent}"
            )


# ============================================================
# HEALTH TIPS PAGE
# ============================================================

if (
    st.session_state.current_page
    == "Health Tips"
):

    st.markdown(
        '<div class="section-title">'
        '🌱 Healthy Lifestyle Tips'
        '</div>',
        unsafe_allow_html=True
    )

    tips = [

        (
            "💧 Stay Hydrated",
            "Drink enough water throughout the day."
        ),

        (
            "🥗 Eat Balanced Meals",
            "Include vegetables, fruits, proteins, and whole grains."
        ),

        (
            "🏃 Stay Active",
            "Regular physical activity supports overall health."
        ),

        (
            "😴 Sleep Well",
            "Maintain a consistent and healthy sleep schedule."
        ),

        (
            "🧘 Manage Stress",
            "Use healthy relaxation techniques and take regular breaks."
        ),

        (
            "🧼 Maintain Hygiene",
            "Wash your hands regularly and maintain personal hygiene."
        )
    ]

    for title, description in tips:

        st.markdown(
            f"""
            <div class="info-card">
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="disclaimer">
        ⚠️ These tips are for general educational purposes only.
        They do not replace professional medical advice.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# ANALYTICS PAGE
# ============================================================

elif (
    st.session_state.current_page
    == "Analytics"
):

    st.markdown(
        '<div class="section-title">'
        '📊 Analytics Dashboard'
        '</div>',
        unsafe_allow_html=True
    )

    if show_analytics is not None:

        try:

            show_analytics()

        except Exception as e:

            st.error(
                f"Unable to load analytics: {str(e)}"
            )

    else:

        st.info(
            "Analytics dashboard module is not available."
        )


# ============================================================
# CONTACT PAGE
# ============================================================

elif (
    st.session_state.current_page
    == "Contact"
):

    st.markdown(
        '<div class="section-title">'
        '📞 Contact & Information'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-card">

        <h3>🩺 About Health Assistant</h3>

        <p>
        This project is an AI-powered educational health assistant
        designed to provide general information about symptoms,
        prevention, self-care, and healthy lifestyle topics.
        </p>

        <h3>⚠️ Important</h3>

        <p>
        This application is for educational purposes only.
        </p>

        <p>
        It is not a doctor, medical professional, diagnostic system,
        or emergency medical service.
        </p>

        <p>
        Always consult a qualified healthcare professional for
        personal medical advice.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# MAIN HEALTH ASSISTANT PAGE
# ============================================================

else:

    # ========================================================
    # QUICK TOPIC PROCESSING
    # ========================================================

    if st.session_state.process_quick_topic:

        topic = (
            st.session_state.quick_topic
        )

        prompt = (
            f"Please provide educational information about "
            f"{topic}. Explain the overview, common symptoms, "
            f"prevention tips, self-care guidance, and when someone "
            f"should consider speaking with a healthcare professional."
        )

        st.session_state.process_quick_topic = False
        st.session_state.quick_topic = None

        process_user_message(
            prompt
        )

        st.rerun()

    # ========================================================
    # INFORMATION CARDS
    # ========================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            <div class="info-card">

            <h3>📚 Symptom Education</h3>

            <p>
            Learn about common symptoms and general health
            information in simple language.
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            """
            <div class="info-card">

            <h3>🛡️ Prevention</h3>

            <p>
            Explore general prevention strategies and healthy
            lifestyle habits.
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            """
            <div class="info-card">

            <h3>💡 Self-Care</h3>

            <p>
            Learn about general self-care approaches and when
            professional medical guidance may be appropriate.
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # CONVERSATION
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        '💬 Conversation'
        '</div>',
        unsafe_allow_html=True
    )

    # ========================================================
    # DISPLAY CHAT HISTORY
    # ========================================================

    for message in st.session_state.messages:

        if message["role"] == "user":

            with st.chat_message("user"):

                st.markdown(
                    message["content"]
                )

        else:

            with st.chat_message(
                "assistant",
                avatar="🩺"
            ):

                cleaned_content = (
                    clean_ai_response(
                        message["content"]
                    )
                )

                st.markdown(
                    cleaned_content
                )

    # ========================================================
    # VOICE INPUT
    # ========================================================

    st.markdown(
        "### 🎤 Voice Input"
    )

    if get_voice_input is not None:

        if st.button(
            "🎙️ Start Voice Input",
            use_container_width=False
        ):

            try:

                voice_text = get_voice_input()

                if voice_text:

                    st.session_state.voice_text = (
                        voice_text
                    )

                    st.rerun()

            except Exception as e:

                st.error(
                    f"Voice input failed: {str(e)}"
                )

    else:

        st.info(
            "Voice input module is not available."
        )

    # ========================================================
    # VOICE MESSAGE PROCESSING
    # ========================================================

    if st.session_state.voice_text:

        prompt = (
            st.session_state.voice_text
        )

        st.session_state.voice_text = ""

        process_user_message(
            prompt
        )

        st.rerun()

    # ========================================================
    # TEXT CHAT
    # ========================================================

    prompt = st.chat_input(
        "Ask a health education question..."
    )

    if prompt:

        process_user_message(
            prompt
        )

        st.rerun()

    # ========================================================
    # DISCLAIMER
    # ========================================================

    st.markdown(
        """
        <div class="disclaimer">

        ⚠️ <strong>Medical Disclaimer</strong>

        <br><br>

        This AI assistant provides general educational information
        only. It cannot diagnose medical conditions, prescribe
        medication, or replace professional medical advice.

        If you have serious or emergency symptoms, contact a
        qualified healthcare professional or local emergency service.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <br>
    <hr>

    <div style="text-align:center; color:#64748b;">

    🩺 Health Assistant • AI-Powered Health Education

    <br><br>

    Built for educational purposes •

    Not a medical diagnostic system

    </div>
    """,
    unsafe_allow_html=True
)
