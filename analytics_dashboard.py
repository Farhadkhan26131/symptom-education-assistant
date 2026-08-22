import streamlit as st
import pandas as pd
from datetime import datetime

def show_analytics_dashboard(db):
    st.subheader("📊 Analytics Dashboard")
    
    analytics = db.get_analytics()
    
    if analytics["total_queries"] == 0:
        st.info("No data available yet. Start asking questions!")
        return
    
    # Summary Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Queries", analytics["total_queries"])
    with col2:
        if analytics["age_groups"]:
            top_age = max(analytics["age_groups"], key=analytics["age_groups"].get)
            st.metric("Most Used Age", top_age)
    with col3:
        if analytics["languages"]:
            top_lang = max(analytics["languages"], key=analytics["languages"].get)
            st.metric("Top Language", top_lang)
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        if analytics["age_groups"]:
            st.subheader("📊 Queries by Age Group")
            df_age = pd.DataFrame({
                "Age Group": list(analytics["age_groups"].keys()),
                "Queries": list(analytics["age_groups"].values())
            })
            st.bar_chart(df_age.set_index("Age Group"))
    
    with col2:
        if analytics["languages"]:
            st.subheader("🌐 Queries by Language")
            df_lang = pd.DataFrame({
                "Language": list(analytics["languages"].keys()),
                "Queries": list(analytics["languages"].values())
            })
            st.bar_chart(df_lang.set_index("Language"))
    
    # Recent Queries
    st.subheader("📝 Recent Conversations")
    recent = db.get_recent_conversations(5)
    if recent:
        for conv in reversed(recent):
            with st.expander(f"📅 {conv['timestamp'][:10]} - {conv['age_group']} - {conv['query_count']} queries"):
                for msg in conv["messages"]:
                    if msg["role"] == "user":
                        st.write(f"**User:** {msg['content'][:100]}...")
                    else:
                        st.write(f"**Assistant:** {msg['content'][:150]}...")