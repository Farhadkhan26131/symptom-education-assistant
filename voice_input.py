import streamlit as st
import speech_recognition as sr

def get_voice_input():
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            with st.spinner("🎤 Listening... Speak now!"):
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        st.error("🔊 Could not understand. Please try again.")
    except sr.RequestError:
        st.error("🌐 Internet connection error.")
    except Exception as e:
        st.error(f"🎤 Error: {str(e)}")
    return None