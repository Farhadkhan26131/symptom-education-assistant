import speech_recognition as sr

def test_microphone():
    print("🔍 Checking microphones...")
    
    try:
        mic_list = sr.Microphone.list_microphone_names()
        
        if not mic_list:
            print("❌ No microphone found!")
            print("Please connect a microphone and try again.")
            return
        
        print("\n✅ Available microphones:")
        for i, name in enumerate(mic_list):
            print(f"  {i}: {name}")
        
        print("\n🎤 Testing first microphone...")
        
        recognizer = sr.Recognizer()
        
        with sr.Microphone() as source:
            print("👂 Listening... Speak something!")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            print("✅ Recording complete!")
            
            print("🔍 Recognizing speech...")
            text = recognizer.recognize_google(audio)
            print(f"\n📝 You said: '{text}'")
            print("\n✅ Microphone is working perfectly!")
            
    except sr.WaitTimeoutError:
        print("⏱️ No speech detected. Please speak louder or check your microphone.")
    except sr.UnknownValueError:
        print("🔊 Could not understand. Please speak clearly.")
    except sr.RequestError:
        print("🌐 Internet connection error. Please check your connection.")
    except OSError as e:
        if "No Default Input Device Available" in str(e):
            print("🎤 No microphone detected. Please connect a microphone.")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_microphone()