import streamlit as st
import time
import random
import re
from datetime import datetime

# ============================================================
# AGENT IMPORT
# ============================================================
from agent import HealthAgent
from database import ChatDatabase


# ============================================================
# OPTIONAL IMPORTS
# ============================================================
try:
    from analytics_dashboard import show_analytics
except ImportError:
    show_analytics = None

try:
    from voice_input import get_voice_input
except ImportError:
    get_voice_input = None

try:
    from pdf_export import create_pdf
except ImportError:
    create_pdf = None


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
# DATABASE
# ============================================================
db = ChatDatabase()


# ============================================================
# HEALTH AGENT
# ============================================================
health_agent = HealthAgent()


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm your Health Assistant. "
                "I can provide general educational information about "
                "symptoms, prevention, self-care, and healthy habits. "
                "Please remember that I am not a doctor and cannot "
                "diagnose or treat medical conditions."
            )
        }
    ]

if "age_group" not in st.session_state:
    st.session_state.age_group = "Adults"

if "language" not in st.session_state:
    st.session_state.language = "English"

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

if "quick_topic" not in st.session_state:
    st.session_state.quick_topic = None

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if "process_quick_topic" not in st.session_state:
    st.session_state.process_quick_topic = False

if "user_id" not in st.session_state:
    st.session_state.user_id = str(random.randint(1000, 9999))

if "current_page" not in st.session_state:
    st.session_state.current_page = "Health Assistant"

if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""


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
    Clean accidental HTML and Streamlit artifacts
    from AI-generated responses.
    """

    if not text:
        return ""

    text = str(text)

    # Remove SVG/anchor artifacts
    text = re.sub(
        r'\[\s*svg\s*\]\([^)]*\)',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Remove accidental Health Assistant HTML wrapper
    text = re.sub(
        r'<strong>\s*\*?\s*🩺\s*Health Assistant\s*\*?\s*</strong>',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Convert <br> to newline
    text = re.sub(
        r'<br\s*/?>',
        '\n',
        text,
        flags=re.IGNORECASE
    )

    # Remove div tags
    text = re.sub(
        r'</?div[^>]*>',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Remove markdown code fences
    text = re.sub(
        r'```(?:html)?\s*',
        '',
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r'\s*```',
        '',
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r'\n{4,}',
        '\n\n',
        text
    )

    return text.strip()


# ============================================================
# SHORT-TERM MEMORY
# ============================================================
def get_conversation_history():
    if len(st.session_state.messages) <= 1:
        return []

    return st.session_state.messages[:-1]


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

        .chat-user,
        .chat-assistant {
            background-color: white;
            color: #0f172a;
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

    st.markdown("## 🩺 Health Assistant")
    st.markdown("---")

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
        ].index(st.session_state.current_page)
    )

    st.session_state.current_page = page

    st.markdown("---")
    st.markdown("### ⚙️ Settings")

    st.session_state.theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=["Dark", "Light"].index(
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

    st.markdown("---")
    st.markdown("### 🏥 Health Categories")

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
        list(disease_categories.keys())
    )

    selected_topic = st.selectbox(
        "Select Topic",
        disease_categories[selected_category]
    )

    if st.button(
        "Learn About Topic",
        use_container_width=True
    ):
        st.session_state.quick_topic = selected_topic
        st.session_state.process_quick_topic = True
        st.rerun()

    st.markdown("---")
    st.markdown("### 🛠️ Actions")

    if st.button(
        "🗑️ Clear Old Chats",
        use_container_width=True
    ):

        st.session_state.messages = [
            st.session_state.messages[0]
        ]

        st.success("Conversation history cleared.")
        st.rerun()

    if st.button(
        "🔄 Reset Everything",
        use_container_width=True
    ):

        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.rerun()

    st.markdown("---")
    st.markdown("### 📄 Export")

    if st.button(
        "Export Conversation",
        use_container_width=True
    ):

        if create_pdf is not None:

            try:

                pdf_file = create_pdf(
                    st.session_state.messages
                )

                if pdf_file:

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
                    f"PDF export failed: {str(e)}"
                )

        else:

            st.warning(
                "PDF export module is not available."
            )

    st.markdown("---")

    st.caption(
        f"Session ID: {st.session_state.user_id}"
    )

    st.caption(
        f"Questions: {st.session_state.query_count}"
    )


# ============================================================
# HEALTH TIPS PAGE
# ============================================================
if st.session_state.current_page == "Health Tips":

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
elif st.session_state.current_page == "Analytics":

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
elif st.session_state.current_page == "Contact":

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

        topic = st.session_state.quick_topic

        prompt = (
            f"Please provide educational information about "
            f"{topic}. Explain the overview, common symptoms, "
            f"prevention tips, self-care guidance, and when someone "
            f"should consider speaking with a healthcare professional."
        )

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        conversation_history = get_conversation_history()

        if not check_rate_limit(
            st.session_state.user_id
        ):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            with st.spinner("🧠 Thinking..."):

                try:

                    response = health_agent.run(
                        user_input=prompt,
                        age_group=st.session_state.age_group,
                        language=st.session_state.language,
                        conversation_history=conversation_history
                    )

                    response = clean_ai_response(response)

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        try:

            db.add_conversation(
                st.session_state.user_id,
                st.session_state.messages,
                st.session_state.age_group,
                st.session_state.language,
                st.session_state.query_count
            )

        except Exception:
            pass

        st.session_state.process_quick_topic = False
        st.session_state.quick_topic = None

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

                cleaned_content = clean_ai_response(
                    message["content"]
                )

                st.markdown(
                    cleaned_content
                )


    # ========================================================
    # VOICE INPUT
    # ========================================================
    st.markdown("### 🎤 Voice Input")

    if get_voice_input is not None:

        if st.button(
            "🎙️ Start Voice Input",
            use_container_width=False
        ):

            try:

                voice_text = get_voice_input()

                if voice_text:

                    st.session_state.voice_text = voice_text
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

        prompt = st.session_state.voice_text

        st.session_state.voice_text = ""

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        conversation_history = get_conversation_history()

        if not check_rate_limit(
            st.session_state.user_id
        ):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            with st.spinner("🧠 Thinking..."):

                try:

                    response = health_agent.run(
                        user_input=prompt,
                        age_group=st.session_state.age_group,
                        language=st.session_state.language,
                        conversation_history=conversation_history
                    )

                    response = clean_ai_response(response)

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        try:

            db.add_conversation(
                st.session_state.user_id,
                st.session_state.messages,
                st.session_state.age_group,
                st.session_state.language,
                st.session_state.query_count
            )

        except Exception:
            pass

        st.rerun()


    # ========================================================
    # TEXT CHAT
    # ========================================================
    prompt = st.chat_input(
        "Ask a health education question..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        conversation_history = get_conversation_history()

        if not check_rate_limit(
            st.session_state.user_id
        ):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            with st.spinner("🧠 Thinking..."):

                try:

                    response = health_agent.run(
                        user_input=prompt,
                        age_group=st.session_state.age_group,
                        language=st.session_state.language,
                        conversation_history=conversation_history
                    )

                    response = clean_ai_response(response)

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        try:

            db.add_conversation(
                st.session_state.user_id,
                st.session_state.messages,
                st.session_state.age_group,
                st.session_state.language,
                st.session_state.query_count
            )

        except Exception:
            pass

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

    Built for educational purposes • Not a medical diagnostic system

    </div>
    """,
    unsafe_allow_html=True
)