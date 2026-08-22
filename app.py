import streamlit as st
from gemini_agent import run_gemini_with_retry
from database import ChatDatabase
from analytics_dashboard import show_analytics_dashboard
from voice_input import get_voice_input
from datetime import datetime
import random
import time
import os

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Symptom Education Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# DATABASE INIT
# ============================================
db = ChatDatabase()

# ============================================
# SESSION STATE
# ============================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": """Welcome to Symptom Education Assistant.

I provide educational health information for all age groups. Feel free to ask about any symptom or disease.

How can I help you today?"""
    }]

if "age_group" not in st.session_state:
    st.session_state.age_group = "All Ages"

if "language" not in st.session_state:
    st.session_state.language = "English"

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

if "quick_topic" not in st.session_state:
    st.session_state.quick_topic = None

if "theme" not in st.session_state:
    st.session_state.theme = "Light"

if "process_quick_topic" not in st.session_state:
    st.session_state.process_quick_topic = False

if "user_id" not in st.session_state:
    st.session_state.user_id = "user_" + str(random.randint(1000, 9999))

if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat"

if "voice_text" not in st.session_state:
    st.session_state.voice_text = None

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT = 20
rate_limit_data = {}

def check_rate_limit(user_id):
    """Check if user has exceeded rate limit"""
    now = datetime.now()
    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = []
    
    from datetime import timedelta
    rate_limit_data[user_id] = [t for t in rate_limit_data[user_id] 
                                 if now - t < timedelta(minutes=1)]
    
    if len(rate_limit_data[user_id]) >= RATE_LIMIT:
        return False
    
    rate_limit_data[user_id].append(now)
    return True

# ============================================
# THEMES
# ============================================
THEMES = {
    "Light": {
        "bg": "#f0f2f5",
        "card": "#ffffff",
        "card2": "#f8f9fa",
        "border": "#e0e0e0",
        "text": "#1a1a2e",
        "text2": "#4a4a6a",
        "text3": "#2a2a4a",
        "accent": "#4f46e5",
        "accent2": "#818cf8",
        "user_msg": "#4f46e5",
        "assistant_msg": "#f0f4ff",
        "sidebar": "#ffffff",
        "input": "#ffffff",
        "hover": "#4f46e5",
        "shadow": "rgba(0,0,0,0.06)"
    },
    "Dark": {
        "bg": "#0d1117",
        "card": "#161b22",
        "card2": "#1c2333",
        "border": "#30363d",
        "text": "#f0f6fc",
        "text2": "#8b949e",
        "text3": "#c9d1d9",
        "accent": "#58a6ff",
        "accent2": "#79c0ff",
        "user_msg": "#1f6feb",
        "assistant_msg": "#1c2333",
        "sidebar": "#0d1117",
        "input": "#0d1117",
        "hover": "#58a6ff",
        "shadow": "rgba(0,0,0,0.4)"
    },
    "Blue": {
        "bg": "#f0f4ff",
        "card": "#ffffff",
        "card2": "#e8edf8",
        "border": "#d0d9e8",
        "text": "#1a2332",
        "text2": "#4a6a8a",
        "text3": "#2a3a5a",
        "accent": "#2563eb",
        "accent2": "#60a5fa",
        "user_msg": "#2563eb",
        "assistant_msg": "#e8edf8",
        "sidebar": "#ffffff",
        "input": "#ffffff",
        "hover": "#2563eb",
        "shadow": "rgba(37,99,235,0.08)"
    }
}

# ============================================
# DISEASE CATEGORIES
# ============================================
CATEGORIES = {
    "🫀 Heart & Blood": [
        "Diabetes", "Hypertension", "Heart Disease", 
        "High Cholesterol", "Stroke", "Anemia"
    ],
    "🧠 Brain & Mental": [
        "Depression", "Anxiety", "Migraine", 
        "Memory Loss", "Dementia", "Stress"
    ],
    "🫁 Breathing": [
        "Asthma", "Pneumonia", "COPD", 
        "Bronchitis", "Cough", "Shortness of Breath"
    ],
    "🦴 Bones & Joints": [
        "Arthritis", "Osteoporosis", "Back Pain", 
        "Gout", "Joint Pain", "Rheumatoid Arthritis"
    ],
    "🌿 General Health": [
        "Fever", "Fatigue", "Allergies", 
        "Headache", "Sore Throat", "Dizziness"
    ],
    "🍽️ Digestive": [
        "Gastritis", "Nausea", "Stomach Pain", 
        "Food Poisoning", "Heartburn", "Indigestion"
    ],
    "🧬 Infectious": [
        "Flu", "Chickenpox", "Measles", 
        "Mumps", "TB", "Hepatitis"
    ],
    "👶 Children's Health": [
        "Childhood Vaccines", "Fever in Children", 
        "Cough in Children", "Chickenpox", "Measles"
    ],
    "👩 Women's Health": [
        "PCOS", "Pregnancy", "Menopause", 
        "Breast Health", "Osteoporosis"
    ],
    "👨 Men's Health": [
        "Prostate Health", "Testosterone", 
        "Heart Health", "ED"
    ],
    "🧴 Skin & Hair": [
        "Eczema", "Acne", "Rash", 
        "Hair Loss", "Psoriasis"
    ],
    "👴 Elderly Health": [
        "Memory Loss", "Fall Prevention", 
        "Arthritis", "Heart Health", "Dementia"
    ]
}

# ============================================
# CSS
# ============================================
current_theme = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }}
    
    .stApp {{
        background: {current_theme['bg']};
    }}
    
    .main > div {{
        background: {current_theme['card']};
        border-radius: 20px;
        padding: 32px 36px;
        margin: 12px 20px;
        border: 1px solid {current_theme['border']};
        box-shadow: 0 8px 32px {current_theme['shadow']};
    }}
    
    .app-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 20px;
        border-bottom: 2px solid {current_theme['border']};
        margin-bottom: 24px;
    }}
    
    .app-title {{
        font-size: 32px;
        font-weight: 800;
        color: {current_theme['text']} !important;
        letter-spacing: -0.5px;
    }}
    
    .app-title span {{
        color: {current_theme['accent']};
    }}
    
    .app-subtitle {{
        font-size: 14px;
        color: {current_theme['text2']} !important;
        font-weight: 400;
        margin-top: 4px;
    }}
    
    .app-badge {{
        background: {current_theme['accent']};
        color: white !important;
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        box-shadow: 0 4px 12px rgba(79,70,229,0.3);
    }}
    
    .stSidebar {{
        background: {current_theme['sidebar']} !important;
        border-right: 1px solid {current_theme['border']} !important;
        padding: 20px 0 !important;
    }}
    
    .stSidebar * {{
        color: {current_theme['text']} !important;
    }}
    
    .stSidebar .stSelectbox label {{
        color: {current_theme['text2']} !important;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    
    .stSidebar .stSelectbox select {{
        background: {current_theme['card2']} !important;
        border: 1px solid {current_theme['border']} !important;
        color: {current_theme['text']} !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }}
    
    .sidebar-header {{
        padding: 0 20px 20px 20px;
        border-bottom: 2px solid {current_theme['border']};
        margin-bottom: 20px;
    }}
    
    .sidebar-logo {{
        font-size: 24px;
        font-weight: 700;
        color: {current_theme['text']} !important;
    }}
    
    .sidebar-logo span {{
        color: {current_theme['accent']};
    }}
    
    .sidebar-version {{
        font-size: 11px;
        color: {current_theme['text2']} !important;
        margin-top: 2px;
    }}
    
    .section-title {{
        font-size: 11px;
        font-weight: 700;
        color: {current_theme['text2']} !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 0 20px;
        margin: 18px 0 10px 0;
        display: block !important;
        visibility: visible !important;
    }}
    
    .section-divider {{
        height: 2px;
        background: {current_theme['border']};
        margin: 16px 20px;
        border-radius: 4px;
    }}
    
    .stat-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        padding: 0 20px;
        margin-bottom: 16px;
    }}
    
    .stat-card {{
        background: {current_theme['card2']};
        border-radius: 14px;
        padding: 16px 12px;
        text-align: center;
        border: 1px solid {current_theme['border']};
        transition: all 0.3s ease;
    }}
    
    .stat-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 16px {current_theme['shadow']};
    }}
    
    .stat-number {{
        font-size: 30px;
        font-weight: 800;
        color: {current_theme['accent']} !important;
    }}
    
    .stat-label {{
        font-size: 11px;
        color: {current_theme['text2']} !important;
        margin-top: 2px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    
    .stButton > button {{
        background: {current_theme['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        box-shadow: 0 4px 16px rgba(79,70,229,0.3) !important;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 32px rgba(79,70,229,0.5) !important;
    }}
    
    .stChatMessage {{
        border-radius: 16px !important;
        padding: 20px 24px !important;
        margin: 12px 0 !important;
        border: 1px solid {current_theme['border']} !important;
        background: {current_theme['card']} !important;
        color: {current_theme['text']} !important;
        line-height: 1.8 !important;
        font-size: 15px !important;
        animation: fadeInUp 0.5s ease-out !important;
    }}
    
    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    .stChatMessage[data-testid="chat-message-user"] {{
        background: {current_theme['user_msg']} !important;
        color: white !important;
        border: none !important;
        margin-left: 20% !important;
        border-radius: 16px 16px 4px 16px !important;
    }}
    
    .stChatMessage[data-testid="chat-message-user"] * {{
        color: white !important;
    }}
    
    .stChatMessage[data-testid="chat-message-assistant"] {{
        background: {current_theme['assistant_msg']} !important;
        border-left: 4px solid {current_theme['accent']} !important;
        margin-right: 20% !important;
        border-radius: 16px 16px 16px 4px !important;
        color: {current_theme['text']} !important;
    }}
    
    .stChatMessage[data-testid="chat-message-assistant"] * {{
        color: {current_theme['text']} !important;
    }}
    
    /* Voice button style */
    .voice-btn {{
        background: {current_theme['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 50% !important;
        width: 50px !important;
        height: 50px !important;
        font-size: 24px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 16px rgba(79,70,229,0.3) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    
    .voice-btn:hover {{
        transform: scale(1.1) !important;
        box-shadow: 0 8px 32px rgba(79,70,229,0.5) !important;
    }}
    
    .stTextInput input {{
        border-radius: 16px !important;
        border: 2px solid {current_theme['border']} !important;
        padding: 18px 24px !important;
        font-size: 15px !important;
        background: {current_theme['input']} !important;
        color: {current_theme['text']} !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px {current_theme['shadow']};
    }}
    
    .stTextInput input:focus {{
        border-color: {current_theme['accent']} !important;
        box-shadow: 0 0 0 4px rgba(79,70,229,0.15) !important;
    }}
    
    .stTextInput input::placeholder {{
        color: {current_theme['text2']};
        opacity: 0.6;
    }}
    
    .streamlit-expanderHeader {{
        background: {current_theme['card2']} !important;
        border: 1px solid {current_theme['border']} !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        font-weight: 600 !important;
        color: {current_theme['text']} !important;
        transition: all 0.3s ease !important;
        font-size: 14px !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        background: {current_theme['accent']} !important;
        color: white !important;
        transform: translateX(8px);
    }}
    
    .tip-box {{
        background: {current_theme['card2']};
        border-radius: 14px;
        padding: 18px 20px;
        border: 1px solid {current_theme['border']};
        margin: 0 20px;
        font-size: 13px;
        color: {current_theme['text']} !important;
        line-height: 1.6;
        border-left: 4px solid {current_theme['accent']};
    }}
    
    .tip-box strong {{
        color: {current_theme['accent']};
        font-weight: 700;
    }}
    
    .app-footer {{
        text-align: center;
        padding-top: 20px;
        border-top: 2px solid {current_theme['border']};
        margin-top: 20px;
        color: {current_theme['text2']} !important;
        font-size: 12px;
    }}
    
    .app-footer span {{
        color: {current_theme['accent']};
        font-weight: 600;
    }}
    
    @media (max-width: 768px) {{
        .main > div {{
            padding: 16px !important;
            margin: 5px !important;
        }}
        
        .stChatMessage[data-testid="chat-message-user"] {{
            margin-left: 5% !important;
        }}
        
        .stChatMessage[data-testid="chat-message-assistant"] {{
            margin-right: 5% !important;
        }}
        
        .app-title {{
            font-size: 22px !important;
        }}
        
        .stat-grid {{
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}
        
        .app-header {{
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER
# ============================================
st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">🩺 Symptom <span>Education</span></div>
        <div class="app-subtitle">Developed by Farhad Khan · AI-Powered Health Information</div>
    </div>
    <div>
        <span class="app-badge">★ Professional</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="sidebar-logo">Health <span>Assistant</span></div>
        <div class="sidebar-version">Version 3.0 · Professional</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.markdown('<div class="section-title">Navigation</div>', unsafe_allow_html=True)
    page = st.radio(
        "",
        ["💬 Chat", "📊 Analytics", "📄 Export"],
        label_visibility="collapsed"
    )
    st.session_state.current_page = page
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    if page == "💬 Chat":
        st.markdown('<div class="stat-grid">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{st.session_state.query_count}</div>
                <div class="stat-label">Queries</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{len(st.session_state.messages)}</div>
                <div class="stat-label">Messages</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Theme
    st.markdown('<div class="section-title">Theme</div>', unsafe_allow_html=True)
    theme_options = list(THEMES.keys())
    selected_theme = st.selectbox("", theme_options, label_visibility="collapsed")
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Settings
    st.markdown('<div class="section-title">Settings</div>', unsafe_allow_html=True)
    
    languages = ["English", "Urdu", "Hindi", "Spanish", "French", "Arabic"]
    language = st.selectbox("Language", languages, label_visibility="collapsed")
    st.session_state.language = language
    
    age_groups = ["All Ages", "Children (0-12)", "Teens (13-19)", "Young Adults (20-30)", 
                  "Adults (30-50)", "Seniors (50-70)", "Elderly (70+)", "Caregivers"]
    age_group = st.selectbox("Age Group", age_groups, label_visibility="collapsed")
    st.session_state.age_group = age_group
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    if page == "💬 Chat":
        # Categories
        st.markdown('<div class="section-title">Browse Categories</div>', unsafe_allow_html=True)
        
        for category, diseases in CATEGORIES.items():
            with st.expander(f"{category}"):
                for disease in diseases:
                    if st.button(disease, key=f"cat_{category}_{disease}"):
                        st.session_state.quick_topic = f"What is {disease}?"
                        st.session_state.process_quick_topic = True
                        st.rerun()
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Health Tip
        tips = [
            "💧 Stay hydrated - drink 8 glasses of water daily",
            "🚶 Walk 30 minutes every day for heart health",
            "😴 Get 7-8 hours of quality sleep",
            "🥗 Eat colorful vegetables for nutrients",
            "🧘 Practice deep breathing to reduce stress",
            "☀️ Get 15 minutes of sunlight for Vitamin D"
        ]
        st.markdown(f"""
        <div class="tip-box">
            <strong>💡 Health Tip</strong><br>
            {random.choice(tips)}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Actions
        st.markdown('<div class="section-title">Actions</div>', unsafe_allow_html=True)
        
        if st.button("🧹 Clear Old Chats", use_container_width=True):
            if len(st.session_state.messages) > 5:
                system_msg = st.session_state.messages[0]
                st.session_state.messages = [system_msg] + st.session_state.messages[-5:]
                st.rerun()
        
        if st.button("🔄 Reset Everything", use_container_width=True):
            st.session_state.messages = []
            st.session_state.query_count = 0
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Welcome back. How can I assist you with your health questions?"
            })
            st.rerun()
    
    elif page == "📄 Export":
        st.markdown('<div class="section-title">Export Options</div>', unsafe_allow_html=True)
        
        if st.button("📥 Export Chat (TXT)", use_container_width=True):
            if st.session_state.messages:
                chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
                st.download_button(
                    label="💾 Download",
                    data=chat_text,
                    file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        if st.button("📄 Export PDF", use_container_width=True):
            st.warning("⚠️ PDF export requires fpdf library. Install with: pip install fpdf")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ============================================
    # CONTACT INFORMATION - FARHAD KHAN
    # ============================================
    st.markdown('<div class="section-title">Connect with Me</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="text-align: center;">
            <a href="https://www.linkedin.com/in/farhad-khan-marwat-41501437a" target="_blank" style="text-decoration: none; font-size: 28px;">🔗</a>
            <br>
            <span style="font-size: 10px; color: #6c757d;">LinkedIn</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="text-align: center;">
            <a href="https://github.com/Farhadkhan26131" target="_blank" style="text-decoration: none; font-size: 28px;">🐙</a>
            <br>
            <span style="font-size: 10px; color: #6c757d;">GitHub</span>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="text-align: center;">
            <a href="https://farhad-ai-portfolio.web.app" target="_blank" style="text-decoration: none; font-size: 28px;">🌐</a>
            <br>
            <span style="font-size: 10px; color: #6c757d;">Portfolio</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding: 8px 0;">
        <a href="mailto:farhadkhan96622@gmail.com" style="text-decoration: none; font-size: 13px; color: #6c757d;">📧 farhadkhan96622@gmail.com</a>
        <br>
        <span style="font-size: 12px; color: #6c757d;">📱 +92 348 9423635</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; font-size: 11px; color: #6c757d; padding: 10px 0;">
        Made with ❤️ by Farhad Khan
    </div>
    """, unsafe_allow_html=True)

# ============================================
# PAGE ROUTING
# ============================================
if st.session_state.current_page == "📊 Analytics":
    show_analytics_dashboard(db)

elif st.session_state.current_page == "📄 Export":
    st.info("📄 Use the sidebar to export your chat history or generate PDF reports.")
    
    st.subheader("📝 Recent Conversations")
    recent = db.get_recent_conversations(5)
    if recent:
        for conv in reversed(recent):
            with st.expander(f"📅 {conv['timestamp'][:10]} - {conv['age_group']} - {conv['query_count']} queries"):
                for msg in conv["messages"][-4:]:
                    if msg["role"] == "user":
                        st.write(f"**User:** {msg['content'][:100]}...")
                    else:
                        st.write(f"**Assistant:** {msg['content'][:150]}...")
    else:
        st.info("No conversations yet. Start chatting!")

else:
    # ============================================
    # PROCESS QUICK TOPIC
    # ============================================
    if st.session_state.process_quick_topic and st.session_state.quick_topic:
        prompt = st.session_state.quick_topic
        st.session_state.query_count += 1
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if not check_rate_limit(st.session_state.user_id):
            st.error("⏳ Too many requests. Please wait.")
            st.stop()
        
        with st.spinner("Analyzing..."):
            response = run_gemini_with_retry(prompt, st.session_state.age_group, st.session_state.language)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        db.add_conversation(
            st.session_state.user_id,
            st.session_state.messages,
            st.session_state.age_group,
            st.session_state.language,
            1
        )
        
        st.session_state.quick_topic = None
        st.session_state.process_quick_topic = False
        st.rerun()

    # ============================================
    # DISPLAY MESSAGES
    # ============================================
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ============================================
    # CHAT INPUT WITH VOICE
    # ============================================
    
    # Create layout with voice button
    col1, col2 = st.columns([5, 1])
    
    with col1:
        prompt = st.chat_input("Ask about a symptom or disease...")
    
    with col2:
        if st.button("🎤", help="Click to speak your question"):
            voice_text = get_voice_input()
            if voice_text:
                st.session_state.voice_text = voice_text
                st.rerun()
    
    # Handle voice input
    if "voice_text" in st.session_state and st.session_state.voice_text:
        prompt = st.session_state.voice_text
        st.session_state.voice_text = None
        
        st.session_state.query_count += 1
        
        if not check_rate_limit(st.session_state.user_id):
            st.error("⏳ Too many requests. Please wait.")
            st.stop()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Analyzing..."):
            try:
                response = run_gemini_with_retry(prompt, st.session_state.age_group, st.session_state.language)
            except Exception as e:
                response = "Unable to process your request. Please try again."
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        db.add_conversation(
            st.session_state.user_id,
            st.session_state.messages,
            st.session_state.age_group,
            st.session_state.language,
            1
        )
        
        st.rerun()
    
    # Handle text input
    if prompt:
        st.session_state.query_count += 1
        
        if not check_rate_limit(st.session_state.user_id):
            st.error("⏳ Too many requests. Please wait.")
            st.stop()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Analyzing..."):
            try:
                response = run_gemini_with_retry(prompt, st.session_state.age_group, st.session_state.language)
            except Exception as e:
                response = "Unable to process your request. Please try again."
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        db.add_conversation(
            st.session_state.user_id,
            st.session_state.messages,
            st.session_state.age_group,
            st.session_state.language,
            1
        )
        
        st.rerun()

# ============================================
# FOOTER
# ============================================
st.markdown(f"""
<div class="app-footer">
    ⚠️ Educational information only · Consult a healthcare professional for medical advice<br>
    Developed by <span>Farhad Khan</span> · 2026
</div>
""", unsafe_allow_html=True)