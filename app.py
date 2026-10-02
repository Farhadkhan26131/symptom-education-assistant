"""
AI Health Education Assistant - Streamlit Application Layer (Upgraded)
Long-Term Memory Integrated.
"""

import streamlit as st
import time
import random
import re
from datetime import datetime

from agent import HealthAgent
from database import ChatDatabase
from session_manager import SessionManager
from user_profile import load_profile, save_profile, add_past_topic, get_profile_context

try:
    from gemini_agent import run_gemini_with_retry
except ImportError:
    run_gemini_with_retry = None

try:
    from analytics_dashboard import show_analytics
except ImportError:
    show_analytics = None

try:
    from voice_input import get_voice_input
except ImportError:
    get_voice_input = None

try:
    from pdf_export import create_pdf, generate_health_report
except ImportError:
    create_pdf = None
    generate_health_report = None

try:
    from mcp_tools import get_mcp_symptom_tool
except ImportError:
    get_mcp_symptom_tool = None

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Health Assistant", page_icon="🩺", layout="wide", initial_sidebar_state="expanded")

# ============================================================
# CONFIGURATION
# ============================================================
MAX_CONTEXT_MESSAGES = 12
SESSION_TTL_HOURS = 24
SUMMARY_TRIGGER = MAX_CONTEXT_MESSAGES + 6
MAX_SUMMARY_ITEMS = 6
MAX_TOOL_CONTEXT_CHARS = 1200

db = ChatDatabase()
health_agent = HealthAgent()
session_manager = SessionManager(sessions_dir="sessions", ttl_hours=SESSION_TTL_HOURS)

# ============================================================
# LONG-TERM MEMORY LOAD
# ============================================================
persistent_profile = load_profile()

DEFAULT_GREETING = {
    "role": "assistant",
    "content": ("👋 Hello! I'm your Health Assistant. I can provide general educational information about symptoms, prevention, self-care, and healthy habits. Please remember that I am not a doctor and cannot diagnose or treat medical conditions.")
}

# ============================================================
# RATE LIMITER
# ============================================================
rate_limit_data = {}
MAX_REQUESTS = 20
TIME_WINDOW = 60

def check_rate_limit(user_id):
    current_time = time.time()
    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = []
    rate_limit_data[user_id] = [t for t in rate_limit_data[user_id] if current_time - t < TIME_WINDOW]
    if len(rate_limit_data[user_id]) >= MAX_REQUESTS:
        return False
    rate_limit_data[user_id].append(current_time)
    return True

# ============================================================
# CLEAN AI RESPONSE
# ============================================================
def clean_ai_response(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\[?\s*svg\s*\]?\([^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<strong>\s*[/\\*]*\s*🩺\s*Health Assistant\s*[/\\*]*\s*</strong>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```(?:html)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```", "", text)
    text = re.sub(r"\n{4,}", "\n\n", text)
    return text.strip()

# ============================================================
# SUMMARIZATION MEMORY
# ============================================================
def summarize_old_history(old_messages):
    if not old_messages:
        return ""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
    summary_prompt = f"""
    Summarize the following health conversation into 3-4 key points.
    Focus on: symptoms mentioned, age group, and any health topics discussed.

    CONVERSATION:
    {history_text}

    SUMMARY:
    """
    try:
        summary = run_gemini_with_retry(
            user_input=summary_prompt,
            age_group="All Ages",
            language="English",
            conversation_history=[],
            summary="",
            tool_result=None
        )
        return summary[:1000]
    except Exception as e:
        print(f"⚠️ Summarization failed: {e}")
        user_msgs = [m['content'] for m in old_messages if m['role'] == 'user']
        return "Earlier topics: " + "; ".join(user_msgs[-3:])

# ============================================================
# SESSION INITIALIZATION
# ============================================================
def initialize_session():
    if "session_id" in st.session_state:
        existing_session_id = st.session_state.session_id
        saved_session = session_manager.load_session(existing_session_id)
        if saved_session is not None:
            state = saved_session.get("state", {})
            st.session_state.messages = state.get("history", [DEFAULT_GREETING.copy()])
            st.session_state.summary = state.get("summary", "")
            st.session_state.scratchpad = state.get("scratchpad", {})
            st.session_state.last_tool_result = state.get("last_tool_result", None)
            st.session_state.plan_step = state.get("plan_step", 0)
            st.session_state.turn_state = state.get("turn_state", {})
            preferences = state.get("preferences", {})
            st.session_state.age_group = preferences.get("age_group", persistent_profile.get("age_group", "Adults"))
            st.session_state.language = preferences.get("language", persistent_profile.get("language", "English"))
            st.session_state.theme = preferences.get("theme", "Dark")
            st.session_state.query_count = state.get("query_count", 0)
            return
        st.session_state.pop("session_id", None)

    initial_state = {
        "history": [DEFAULT_GREETING.copy()],
        "summary": "",
        "scratchpad": {},
        "last_tool_result": None,
        "plan_step": 0,
        "turn_state": {},
        "preferences": {
            "age_group": persistent_profile.get("age_group", "Adults"),
            "language": persistent_profile.get("language", "English"),
            "theme": "Dark"
        },
        "query_count": 0
    }
    new_session = session_manager.create_session(initial_state=initial_state)
    st.session_state.session_id = new_session["session_id"]
    st.session_state.messages = initial_state["history"]
    st.session_state.summary = initial_state["summary"]
    st.session_state.scratchpad = initial_state["scratchpad"]
    st.session_state.last_tool_result = initial_state["last_tool_result"]
    st.session_state.plan_step = initial_state["plan_step"]
    st.session_state.turn_state = initial_state["turn_state"]
    st.session_state.age_group = initial_state["preferences"]["age_group"]
    st.session_state.language = initial_state["preferences"]["language"]
    st.session_state.theme = "Dark"
    st.session_state.query_count = 0

initialize_session()

if "quick_topic" not in st.session_state: st.session_state.quick_topic = None
if "process_quick_topic" not in st.session_state: st.session_state.process_quick_topic = False
if "user_id" not in st.session_state: st.session_state.user_id = str(random.randint(1000, 9999))
if "current_page" not in st.session_state: st.session_state.current_page = "Health Assistant"
if "voice_text" not in st.session_state: st.session_state.voice_text = ""

# ============================================================
# SAVE CURRENT SESSION
# ============================================================
def save_current_session():
    state = {
        "history": st.session_state.messages,
        "summary": st.session_state.get("summary", ""),
        "scratchpad": st.session_state.get("scratchpad", {}),
        "last_tool_result": st.session_state.get("last_tool_result", None),
        "plan_step": st.session_state.get("plan_step", 0),
        "turn_state": st.session_state.get("turn_state", {}),
        "preferences": {
            "age_group": st.session_state.age_group,
            "language": st.session_state.language,
            "theme": st.session_state.theme
        },
        "query_count": st.session_state.query_count
    }
    try:
        session_manager.save_session(st.session_state.session_id, state)
        return True
    except Exception as e:
        print(f"⚠️ Session save failed: {e}")
        return False

# ============================================================
# SHORT-TERM MEMORY
# ============================================================
def get_conversation_history():
    if len(st.session_state.messages) <= 1:
        return []
    previous_messages = st.session_state.messages[:-1]
    return previous_messages[-MAX_CONTEXT_MESSAGES:]

# ============================================================
# AGENT ROUTING LABEL
# ============================================================
def get_agent_label(intent):
    labels = {
        "emergency": "Emergency Safety Agent",
        "symptom_education": "Symptom Education Agent",
        "prevention": "Prevention Agent",
        "lifestyle": "Lifestyle Agent",
        "general_health": "General Health Agent",
        "follow_up": "Symptom Education Agent"
    }
    return labels.get(intent, "General Health Agent")

# ============================================================
# LOCAL TOOL
# ============================================================
def extract_tool_topic(prompt):
    if not prompt: return None
    text = str(prompt).lower()
    known_topics = ["diabetes", "headache", "fever", "cough", "cold", "flu", "dizziness", "dizzy", "nausea", "vomiting", "diarrhea", "fatigue", "weakness", "rash", "swelling", "pain"]
    for topic in known_topics:
        if topic in text:
            return topic
    return None

def run_local_health_tool(topic, age_group):
    if not topic: return None
    if get_mcp_symptom_tool is None: return None
    try:
        tool = get_mcp_symptom_tool()
        result = tool["function"](symptom=topic, age_group=age_group)
        if result:
            return str(result)[:MAX_TOOL_CONTEXT_CHARS]
    except Exception as e:
        print(f"⚠️ Local health tool failed: {e}")
    return None

# ============================================================
# UNIFIED MESSAGE PROCESSOR
# ============================================================
def process_user_message(prompt):
    if not prompt: return
    prompt = str(prompt).strip()
    if not prompt: return

    if not check_rate_limit(st.session_state.user_id):
        st.warning("You have reached the temporary request limit. Please wait a moment and try again.")
        return

    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        intent = health_agent.detect_intent(prompt)
    except Exception:
        intent = "general_health"

    # ========================================================
    # LONG-TERM MEMORY: Record the topic
    # ========================================================
    if intent in ["symptom_education", "prevention", "lifestyle"]:
        topic = extract_tool_topic(prompt)
        if topic:
            add_past_topic(topic)

    active_agent = get_agent_label(intent)
    tool_topic = None
    tool_result = None

    if intent != "emergency":
        tool_topic = extract_tool_topic(prompt)
        if tool_topic:
            tool_result = run_local_health_tool(topic=tool_topic, age_group=st.session_state.age_group)

    st.session_state.last_tool_result = tool_result
    st.session_state.plan_step += 1
    current_plan_step = st.session_state.plan_step

    st.session_state.turn_state = {
        "status": "processing", "plan_step": current_plan_step, "query_count": st.session_state.query_count + 1,
        "intent": intent, "active_agent": active_agent, "tool_used": bool(tool_result),
        "tool_topic": tool_topic, "started_at": datetime.now().isoformat()
    }

    st.session_state.scratchpad = {
        "last_query": prompt, "intent": intent, "active_agent": active_agent,
        "tool_used": bool(tool_result), "tool_topic": tool_topic,
        "plan_step": current_plan_step, "status": "processing"
    }

    # Summarization memory
    current_summary = st.session_state.get("summary", "")
    if len(st.session_state.messages) > SUMMARY_TRIGGER:
        old_messages = st.session_state.messages[1:-MAX_CONTEXT_MESSAGES]
        current_summary = summarize_old_history(old_messages)
        st.session_state.summary = current_summary

    conversation_history = get_conversation_history()

    # ========================================================
    # LONG-TERM MEMORY: Inject profile into the prompt
    # ========================================================
    profile_context = get_profile_context()
    if profile_context and "No long-term user profile yet" not in profile_context:
        prompt_with_memory = f"{profile_context}\n\nCURRENT QUESTION:\n{prompt}"
    else:
        prompt_with_memory = prompt

    response = ""
    with st.spinner("🧠 Thinking..."):
        try:
            result = health_agent.run(
                user_input=prompt_with_memory,
                age_group=st.session_state.age_group,
                language=st.session_state.language,
                conversation_history=conversation_history
            )

            if isinstance(result, dict):
                response = result.get("response", "")
                returned_intent = result.get("intent")
                returned_agent = result.get("active_agent")
                if returned_intent: intent = returned_intent
                if returned_agent: active_agent = returned_agent
            else:
                response = result

            response = clean_ai_response(response)
            if not response:
                response = "I could not generate a response right now. Please try again."

        except Exception as e:
            print(f"❌ AI processing error: {e}")
            response = "Sorry, I couldn't process your request right now. Please try again later."
            st.session_state.turn_state.update({"status": "error", "error": True, "completed_at": datetime.now().isoformat()})
            save_current_session()

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.query_count += 1

    if len(st.session_state.messages) > SUMMARY_TRIGGER:
        st.session_state.summary = summarize_old_history(st.session_state.messages[1:-MAX_CONTEXT_MESSAGES])

    st.session_state.turn_state.update({
        "status": "completed", "query_count": st.session_state.query_count,
        "intent": intent, "active_agent": active_agent,
        "tool_used": bool(tool_result), "tool_topic": tool_topic,
        "response_available": bool(response), "completed_at": datetime.now().isoformat()
    })

    st.session_state.scratchpad.update({
        "last_query": prompt, "intent": intent, "active_agent": active_agent,
        "tool_used": bool(tool_result), "tool_topic": tool_topic,
        "last_response_available": bool(response), "plan_step": current_plan_step, "status": "completed"
    })

    try:
        db.add_conversation(st.session_state.user_id, st.session_state.messages, st.session_state.age_group, st.session_state.language, 1)
    except Exception as e:
        print(f"⚠️ Database logging failed: {e}")

    save_current_session()

# ============================================================
# DARK THEME
# ============================================================
if st.session_state.theme == "Dark":
    st.markdown("""<style>
        .stApp { background-color: #0f172a !important; color: #f8fafc !important; }
        .main { background-color: #0f172a !important; }
        [data-testid="stSidebar"] { background-color: #111827 !important; }
        [data-testid="stSidebar"] * { color: #f8fafc !important; }
        .main-title { font-size: 42px; font-weight: 800; color: #38bdf8; margin-bottom: 5px; }
        .subtitle { font-size: 18px; color: #94a3b8; margin-bottom: 25px; }
        .section-title { font-size: 28px; font-weight: 700; color: #38bdf8; margin-top: 20px; margin-bottom: 15px; }
        .info-card { padding: 20px; border-radius: 15px; background-color: #1e293b; border: 1px solid #334155; margin-bottom: 15px; color: #f8fafc; }
        .info-card h3 { color: #38bdf8 !important; }
        .info-card p { color: #cbd5e1 !important; }
        [data-testid="stChatMessage"] { background-color: #1e293b !important; border: 1px solid #334155 !important; border-radius: 16px !important; padding: 16px !important; margin-top: 10px !important; margin-bottom: 10px !important; }
        [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] div { color: #f8fafc !important; }
        [data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3, [data-testid="stChatMessage"] h4 { color: #38bdf8 !important; }
        [data-testid="stChatMessage"] strong { color: #f8fafc !important; }
        [data-testid="stChatMessage"] a { color: #7dd3fc !important; }
        [data-testid="stChatInput"] { background-color: #1e293b !important; border: 1px solid #475569 !important; border-radius: 14px !important; }
        [data-testid="stChatInput"] textarea { background-color: #1e293b !important; color: #f8fafc !important; caret-color: #38bdf8 !important; }
        [data-testid="stChatInput"] textarea::placeholder { color: #94a3b8 !important; }
        .stMarkdown { color: #f8fafc; }
        .disclaimer { background-color: #3f2f14; border: 1px solid #854d0e; padding: 15px; border-radius: 10px; color: #fef3c7; margin-top: 20px; }
        footer { visibility: hidden; }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
        .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
        .main { background-color: #f8fafc !important; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; }
        [data-testid="stSidebar"] * { color: #0f172a !important; }
        .main-title { font-size: 42px; font-weight: 800; color: #0284c7; margin-bottom: 5px; }
        .subtitle { font-size: 18px; color: #475569; margin-bottom: 25px; }
        .section-title { font-size: 28px; font-weight: 700; color: #0284c7; margin-top: 20px; margin-bottom: 15px; }
        .info-card { padding: 20px; border-radius: 15px; background-color: white; border: 1px solid #e2e8f0; margin-bottom: 15px; }
        [data-testid="stChatMessage"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 16px !important; padding: 16px !important; margin-top: 10px !important; margin-bottom: 10px !important; }
        [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] div { color: #0f172a !important; }
        [data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3, [data-testid="stChatMessage"] h4 { color: #0284c7 !important; }
        [data-testid="stChatInput"] { background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 14px !important; }
        [data-testid="stChatInput"] textarea { background-color: #ffffff !important; color: #0f172a !important; caret-color: #0284c7 !important; }
        [data-testid="stChatInput"] textarea::placeholder { color: #64748b !important; }
        .disclaimer { background-color: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 10px; color: #78350f; margin-top: 20px; }
        footer { visibility: hidden; }
    </style>""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-title">🩺 Health Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Educational health information powered by AI</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🩺 Health Assistant")
    st.markdown("---")

    page = st.radio("Navigation", ["Health Assistant", "Health Tips", "Analytics", "Contact"], index=["Health Assistant", "Health Tips", "Analytics", "Contact"].index(st.session_state.current_page))
    st.session_state.current_page = page
    st.markdown("---")

    st.markdown("### ⚙️ Settings")
    st.session_state.theme = st.selectbox("Theme", ["Dark", "Light"], index=["Dark", "Light"].index(st.session_state.theme))
    st.session_state.language = st.selectbox("Language", ["English", "Urdu", "Hindi", "Arabic"], index=["English", "Urdu", "Hindi", "Arabic"].index(st.session_state.language))
    st.session_state.age_group = st.selectbox("Age Group", ["Children", "Teenagers", "Adults", "Older Adults"], index=["Children", "Teenagers", "Adults", "Older Adults"].index(st.session_state.age_group))

    # ========================================================
    # LONG-TERM MEMORY: Save preferences permanently
    # ========================================================
    try:
        profile = load_profile()
        profile["age_group"] = st.session_state.age_group
        profile["language"] = st.session_state.language
        save_profile(profile)
    except Exception:
        pass

    save_current_session()
    st.markdown("---")

    st.markdown("### 🏥 Health Categories")
    disease_categories = {
        "🤒 Common Symptoms": ["Headache", "Fever", "Cough", "Cold", "Fatigue"],
        "🫀 Chronic Conditions": ["Diabetes", "High Blood Pressure", "Heart Health"],
        "🧠 Mental Wellness": ["Stress", "Anxiety", "Sleep"],
        "🥗 Healthy Lifestyle": ["Nutrition", "Exercise", "Hydration"]
    }
    selected_category = st.selectbox("Select Category", list(disease_categories.keys()))
    selected_topic = st.selectbox("Select Topic", disease_categories[selected_category])
    if st.button("Learn About Topic", use_container_width=True):
        st.session_state.quick_topic = selected_topic
        st.session_state.process_quick_topic = True
        st.rerun()
    st.markdown("---")

    st.markdown("### 🛠️ Actions")
    if st.button("🗑️ Clear Old Chats", use_container_width=True):
        st.session_state.messages = [DEFAULT_GREETING.copy()]
        st.session_state.summary = ""
        st.session_state.scratchpad = {}
        st.session_state.last_tool_result = None
        st.session_state.plan_step = 0
        st.session_state.turn_state = {}
        st.session_state.query_count = 0
        st.session_state.quick_topic = None
        st.session_state.process_quick_topic = False
        save_current_session()
        st.success("Conversation history cleared.")
        st.rerun()

    if st.button("🔄 Reset Everything", use_container_width=True):
        try:
            session_manager.delete_session(st.session_state.session_id)
        except Exception:
            pass
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.markdown("---")

    st.markdown("### 📄 Export")
    if st.button("Export Conversation", use_container_width=True):
        pdf_file = None
        if create_pdf is not None:
            try:
                pdf_file = create_pdf(st.session_state.messages)
            except Exception as e:
                st.error(f"PDF export failed: {str(e)}")
        elif generate_health_report is not None:
            try:
                last_user = ""
                last_assistant = ""
                for message in reversed(st.session_state.messages):
                    if not last_assistant and message.get("role") == "assistant":
                        last_assistant = message.get("content", "")
                    elif not last_user and message.get("role") == "user":
                        last_user = message.get("content", "")
                    if last_user and last_assistant:
                        break
                if not last_user or not last_assistant:
                    st.warning("There is no completed conversation available to export yet.")
                else:
                    pdf_file = generate_health_report(last_user, last_assistant, st.session_state.age_group, st.session_state.language)
            except Exception as e:
                st.error(f"PDF export failed: {str(e)}")
        if pdf_file:
            try:
                with open(pdf_file, "rb") as file:
                    st.download_button(label="⬇️ Download PDF", data=file, file_name="health_conversation.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Unable to read PDF file: {str(e)}")
        elif create_pdf is None and generate_health_report is None:
            st.warning("PDF export module is not available.")
    st.markdown("---")

    st.markdown("### 💾 Session")
    st.caption(f"Session ID: {st.session_state.session_id}")
    st.caption(f"Questions: {st.session_state.query_count}")
    st.caption(f"Context window: {MAX_CONTEXT_MESSAGES} messages")
    st.caption(f"Memory summary: {'Available' if st.session_state.get('summary') else 'Not needed yet'}")
    if st.session_state.get("turn_state"):
        current_agent = st.session_state.turn_state.get("active_agent")
        if current_agent:
            st.caption(f"Active route: {current_agent}")

    # ========================================================
    # LONG-TERM MEMORY DISPLAY
    # ========================================================
    st.markdown("---")
    st.markdown("### 🧠 Long-Term Memory")
    try:
        profile = load_profile()
        if profile.get("chronic_conditions"):
            st.caption(f"Conditions: {', '.join(profile['chronic_conditions'])}")
        if profile.get("past_topics"):
            st.caption(f"Recent topics: {', '.join(profile['past_topics'][-3:])}")
        if not profile.get("chronic_conditions") and not profile.get("past_topics"):
            st.caption("Learning your preferences...")
    except Exception:
        st.caption("Profile not available.")

# ============================================================
# HEALTH TIPS PAGE
# ============================================================
if st.session_state.current_page == "Health Tips":
    st.markdown('<div class="section-title">🌱 Healthy Lifestyle Tips</div>', unsafe_allow_html=True)
    tips = [
        ("💧 Stay Hydrated", "Drink enough water throughout the day."),
        ("🥗 Eat Balanced Meals", "Include vegetables, fruits, proteins, and whole grains."),
        ("🏃 Stay Active", "Regular physical activity supports overall health."),
        ("😴 Sleep Well", "Maintain a consistent and healthy sleep schedule."),
        ("🧘 Manage Stress", "Use healthy relaxation techniques and take regular breaks."),
        ("🧼 Maintain Hygiene", "Wash your hands regularly and maintain personal hygiene.")
    ]
    for title, description in tips:
        st.markdown(f"""<div class="info-card"><h3>{title}</h3><p>{description}</p></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="disclaimer">⚠️ These tips are for general educational purposes only. They do not replace professional medical advice.</div>""", unsafe_allow_html=True)

elif st.session_state.current_page == "Analytics":
    st.markdown('<div class="section-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    if show_analytics is not None:
        try:
            show_analytics()
        except Exception as e:
            st.error(f"Unable to load analytics: {str(e)}")
    else:
        st.info("Analytics dashboard module is not available.")

elif st.session_state.current_page == "Contact":
    st.markdown('<div class="section-title">📞 Contact & Information</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="info-card">
        <h3>🩺 About Health Assistant</h3>
        <p>This project is an AI-powered educational health assistant designed to provide general information about symptoms, prevention, self-care, and healthy lifestyle topics.</p>
        <h3>⚠️ Important</h3>
        <p>This application is for educational purposes only.</p>
        <p>It is not a doctor, medical professional, diagnostic system, or emergency medical service.</p>
        <p>Always consult a qualified healthcare professional for personal medical advice.</p>
        </div>
    """, unsafe_allow_html=True)

else:
    if st.session_state.process_quick_topic:
        topic = st.session_state.quick_topic
        prompt = f"Please provide educational information about {topic}. Explain the overview, common symptoms, prevention tips, self-care guidance, and when someone should consider speaking with a healthcare professional."
        st.session_state.process_quick_topic = False
        st.session_state.quick_topic = None
        process_user_message(prompt)
        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="info-card"><h3>📚 Symptom Education</h3><p>Learn about common symptoms and general health information in simple language.</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="info-card"><h3>🛡️ Prevention</h3><p>Explore general prevention strategies and healthy lifestyle habits.</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="info-card"><h3>💡 Self-Care</h3><p>Learn about general self-care approaches and when professional medical guidance may be appropriate.</p></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">💬 Conversation</div>', unsafe_allow_html=True)
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar="🩺"):
                cleaned_content = clean_ai_response(message["content"])
                st.markdown(cleaned_content)

    st.markdown("### 🎤 Voice Input")
    if get_voice_input is not None:
        if st.button("🎙️ Start Voice Input", use_container_width=False):
            try:
                voice_text = get_voice_input()
                if voice_text:
                    st.session_state.voice_text = voice_text
                    st.rerun()
            except Exception as e:
                st.error(f"Voice input failed: {str(e)}")
    else:
        st.info("Voice input module is not available.")

    if st.session_state.voice_text:
        prompt = st.session_state.voice_text
        st.session_state.voice_text = ""
        process_user_message(prompt)
        st.rerun()

    prompt = st.chat_input("Ask a health education question...")
    if prompt:
        process_user_message(prompt)
        st.rerun()

    st.markdown("""
        <div class="disclaimer">
        ⚠️ <strong>Medical Disclaimer</strong>
        <br><br>
        This AI assistant provides general educational information only. It cannot diagnose medical conditions, prescribe medication, or replace professional medical advice.
        If you have serious or emergency symptoms, contact a qualified healthcare professional or local emergency service.
        </div>
    """, unsafe_allow_html=True)

st.markdown("""<br><hr><div style="text-align:center; color:#64748b;">🩺 Health Assistant • AI-Powered Health Education<br><br>Built for educational purposes • Not a medical diagnostic system</div>""", unsafe_allow_html=True)