import streamlit as st
import time
import random
from datetime import datetime

from gemini_agent import run_gemini_with_retry
from database import ChatDatabase

# Optional imports
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
                "Please remember that I am not a doctor and cannot diagnose "
                "or treat medical conditions."
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
    """Simple rate limiter."""

    current_time = time.time()

    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = []

    # Remove requests older than TIME_WINDOW
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
# SHORT-TERM MEMORY
# ============================================================

def get_conversation_history():
    """
    Return previous conversation messages.

    The newest user message is already stored in
    st.session_state.messages when this function is called.

    Therefore, messages[:-1] gives us the conversation
    history BEFORE the current question.

    This is Short-Term Memory.
    """

    if len(st.session_state.messages) <= 1:
        return []

    return st.session_state.messages[:-1]


# ============================================================
# THEME
# ============================================================

if st.session_state.theme == "Dark":

    st.markdown(
        """
        <style>

        .stApp {
            background-color: #0f172a;
            color: #f8fafc;
        }

        [data-testid="stSidebar"] {
            background-color: #111827;
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
        }

        .chat-user {
            background-color: #1e3a5f;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
        }

        .chat-assistant {
            background-color: #1e293b;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
            border: 1px solid #334155;
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

else:

    st.markdown(
        """
        <style>

        .stApp {
            background-color: #f8fafc;
            color: #0f172a;
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

        .chat-user {
            background-color: #dbeafe;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
        }

        .chat-assistant {
            background-color: #f1f5f9;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
            border: 1px solid #e2e8f0;
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

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    st.markdown("### ⚙️ Settings")

    st.session_state.theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=["Dark", "Light"].index(st.session_state.theme)
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
        ].index(st.session_state.language)
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
        ].index(st.session_state.age_group)
    )

    st.markdown("---")

    # --------------------------------------------------------
    # HEALTH CATEGORIES
    # --------------------------------------------------------

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

    if st.button("Learn About Topic", use_container_width=True):

        st.session_state.quick_topic = selected_topic
        st.session_state.process_quick_topic = True

        st.rerun()

    st.markdown("---")

    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    st.markdown("### 🛠️ Actions")

    if st.button(
        "🗑️ Clear Old Chats",
        use_container_width=True
    ):

        if len(st.session_state.messages) > 1:

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

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

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

                    with open(pdf_file, "rb") as file:

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

    # --------------------------------------------------------
    # USER INFORMATION
    # --------------------------------------------------------

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
        '<div class="section-title">🌱 Healthy Lifestyle Tips</div>',
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
        '<div class="section-title">📊 Analytics Dashboard</div>',
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
        '<div class="section-title">📞 Contact & Information</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-card">

        ### 🩺 About Health Assistant

        This project is an AI-powered educational health assistant
        designed to provide general information about symptoms,
        prevention, self-care, and healthy lifestyle topics.

        ### ⚠️ Important

        This application is for educational purposes only.

        It is not a doctor, medical professional, diagnostic system,
        or emergency medical service.

        Always consult a qualified healthcare professional for
        personal medical advice.

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# MAIN HEALTH ASSISTANT PAGE
# ============================================================

else:

    # --------------------------------------------------------
    # QUICK TOPIC PROCESSING
    # --------------------------------------------------------

    if st.session_state.process_quick_topic:

        topic = st.session_state.quick_topic

        prompt = (
            f"Please provide educational information about "
            f"{topic}. Explain the overview, common symptoms, "
            f"prevention tips, self-care guidance, and when someone "
            f"should consider speaking with a healthcare professional."
        )

        # Add current user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        # Get PREVIOUS conversation history
        conversation_history = get_conversation_history()

        # Rate limit
        if not check_rate_limit(st.session_state.user_id):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            with st.spinner("🧠 Thinking..."):

                try:

                    response = run_gemini_with_retry(
                        prompt,
                        st.session_state.age_group,
                        st.session_state.language,
                        conversation_history=conversation_history
                    )

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        # Add assistant response
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        # Save conversation
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

    # --------------------------------------------------------
    # INFORMATION CARDS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            <div class="info-card">

            ### 📚 Symptom Education

            Learn about common symptoms and general health
            information in simple language.

            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            """
            <div class="info-card">

            ### 🛡️ Prevention

            Explore general prevention strategies and healthy
            lifestyle habits.

            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            """
            <div class="info-card">

            ### 💡 Self-Care

            Learn about general self-care approaches and when
            professional medical guidance may be appropriate.

            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # RECENT CONVERSATION
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">💬 Conversation</div>',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # DISPLAY CHAT HISTORY
    # --------------------------------------------------------

    for message in st.session_state.messages:

        if message["role"] == "user":

            st.markdown(
                f"""
                <div class="chat-user">

                <strong>👤 You</strong>

                <br><br>

                {message["content"]}

                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div class="chat-assistant">

                <strong>🩺 Health Assistant</strong>

                <br><br>

                {message["content"]}

                </div>
                """,
                unsafe_allow_html=True
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

    # --------------------------------------------------------
    # VOICE MESSAGE PROCESSING
    # --------------------------------------------------------

    if st.session_state.voice_text:

        prompt = st.session_state.voice_text

        st.session_state.voice_text = ""

        # Add user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        # IMPORTANT:
        # Get previous messages AFTER adding the user message.
        # The helper removes the newest message.
        conversation_history = get_conversation_history()

        if not check_rate_limit(st.session_state.user_id):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            with st.spinner("🧠 Thinking..."):

                try:

                    response = run_gemini_with_retry(
                        prompt,
                        st.session_state.age_group,
                        st.session_state.language,
                        conversation_history=conversation_history
                    )

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        # Add assistant response
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        # Save conversation
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

        # ----------------------------------------------------
        # ADD USER MESSAGE
        # ----------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        # ----------------------------------------------------
        # SHORT-TERM MEMORY
        # ----------------------------------------------------
        #
        # IMPORTANT:
        #
        # The current user message has already been added.
        #
        # get_conversation_history()
        # returns all messages BEFORE this current message.
        #
        # Example:
        #
        # User: What is diabetes?
        # Assistant: Diabetes is...
        # User: What are its symptoms?
        #
        # For the second question, Gemini receives:
        #
        # User: What is diabetes?
        # Assistant: Diabetes is...
        #
        # It can therefore understand "its symptoms".
        # ----------------------------------------------------

        conversation_history = get_conversation_history()

        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if not check_rate_limit(st.session_state.user_id):

            response = (
                "You have reached the temporary request limit. "
                "Please wait a moment and try again."
            )

        else:

            # ------------------------------------------------
            # GEMINI REQUEST
            # ------------------------------------------------

            with st.spinner("🧠 Thinking..."):

                try:

                    response = run_gemini_with_retry(
                        prompt,
                        st.session_state.age_group,
                        st.session_state.language,
                        conversation_history=conversation_history
                    )

                except Exception as e:

                    response = (
                        "Sorry, I couldn't process your request right now. "
                        f"Please try again later.\n\nError: {str(e)}"
                    )

        # ----------------------------------------------------
        # ADD ASSISTANT RESPONSE
        # ----------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.session_state.query_count += 1

        # ----------------------------------------------------
        # SAVE CONVERSATION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REFRESH UI
        # ----------------------------------------------------

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