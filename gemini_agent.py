import os
import hashlib
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ============================================
# USE GEMINI API (FREE)
# ============================================
key = os.getenv("GEMINI_API_KEY")

if not key:
    print("⚠️ GEMINI_API_KEY not found in .env file")
    print("Please add: GEMINI_API_KEY='your-key-here'")
    exit()

try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    
    models_to_try = [
        'gemini-3.6-flash',
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash',
        'gemini-1.5-pro'
    ]
    
    model = None
    for model_name in models_to_try:
        try:
            test_model = genai.GenerativeModel(model_name)
            test_model.generate_content("Hello")
            model = test_model
            print(f"✅ Using Gemini model: {model_name}")
            break
        except Exception as e:
            print(f"❌ {model_name} failed: {e}")
            continue
    
    if not model:
        model = genai.GenerativeModel('gemini-3.6-flash')
        
except ImportError:
    print("❌ google-generativeai not installed. Run: pip install google-generativeai")
    exit()

# ============================================
# CACHE SYSTEM
# ============================================
CACHE_FILE = "response_cache.json"

class ResponseCache:
    def __init__(self, cache_duration_hours=24):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache = self.load()
    
    def load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def get_key(self, query, age_group, language):
        return hashlib.md5(f"{query}|{age_group}|{language}".encode()).hexdigest()
    
    def get(self, query, age_group, language):
        key = self.get_key(query, age_group, language)
        if key in self.cache:
            data = self.cache[key]
            if datetime.now() - datetime.fromisoformat(data["timestamp"]) < self.cache_duration:
                return data["response"]
        return None
    
    def set(self, query, age_group, language, response):
        key = self.get_key(query, age_group, language)
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        self.save()

cache = ResponseCache()

# ============================================
# COMPLETE HEALTH KEYWORDS - ALL DISEASES
# ============================================
HEALTH_KEYWORDS = [
    # Symptoms
    'symptom', 'pain', 'ache', 'fever', 'cough', 'cold', 'flu',
    'headache', 'migraine', 'dizzy', 'dizziness', 'vertigo', 'lightheaded',
    'nausea', 'vomit', 'fatigue', 'tired', 'weakness', 
    'swelling', 'inflammation', 'rash', 'itching', 'burning',
    'numbness', 'tingling', 'stiffness',
    
    # Common Diseases
    'diabetes', 'hypertension', 'high blood pressure', 'heart disease',
    'asthma', 'allergy', 'sinusitis', 'pneumonia', 'copd', 'bronchitis',
    'arthritis', 'rheumatoid', 'osteoarthritis', 'gout', 'osteoporosis',
    'fibromyalgia', 'chronic', 'acute',
    'depression', 'anxiety', 'stress', 'panic', 'ptsd',
    'bipolar', 'schizophrenia', 'ocd', 'adhd', 'autism',
    'alzheimer', 'dementia', 'memory loss', 'forget', 'forgetting',
    'parkinson', 'multiple sclerosis', 'epilepsy', 'seizure',
    
    # Infectious Diseases
    'measles', 'mumps', 'rubella', 'chickenpox', 'polio',
    'tetanus', 'diphtheria', 'pertussis', 'whooping cough',
    'hiv', 'aids', 'hepatitis', 'typhoid', 'cholera',
    'malaria', 'dengue', 'zika', 'ebola', 'covid', 'corona',
    'influenza', 'tuberculosis', 'tb', 'food poisoning', 'food pois',
    'strep throat', 'tonsillitis', 'laryngitis', 'pharyngitis',
    'gastroenteritis', 'appendicitis', 'pancreatitis',
    'peritonitis', 'cellulitis', 'abscess', 'boil',
    'warts', 'herpes', 'shingles', 'cold sore',
    'yeast infection', 'thrush', 'ringworm', 'athlete foot',
    
    # Body Parts
    'heart', 'lung', 'kidney', 'liver', 'brain', 'spine',
    'bone', 'joint', 'muscle', 'nerve', 'skin', 'blood',
    'stomach', 'intestine', 'colon', 'rectum', 'bladder',
    'prostate', 'ovary', 'uterus', 'cervix', 'breast', 'breast health',
    'testicle', 'penis', 'vagina', 'pelvic',
    'shoulder', 'knee', 'hip', 'ankle', 'wrist', 'elbow',
    'neck', 'back', 'chest', 'chest pain', 'abdomen', 'head', 'face',
    'eye', 'ear', 'nose', 'throat', 'mouth', 'tooth', 'gum',
    'hair', 'hair loss', 'hairfall', 'bald', 'balding',
    
    # Medical Terms
    'medical', 'doctor', 'hospital', 'clinic', 'pharmacy',
    'medicine', 'pill', 'tablet', 'capsule', 'syrup', 'injection',
    'vaccine', 'vaccination', 'immunization', 'antibiotic',
    'prescription', 'diagnosis', 'treatment', 'therapy',
    'surgery', 'operation', 'emergency', 'ambulance',
    'x-ray', 'mri', 'ct scan', 'ultrasound', 'biopsy',
    'screening', 'checkup', 'physical exam', 'blood test',
    'urine test', 'stool test', 'pap smear', 'mammogram',
    
    # Health & Wellness
    'health', 'wellness', 'fitness', 'exercise', 'diet',
    'nutrition', 'vitamin', 'mineral', 'supplement', 'herbal',
    'sleep', 'insomnia', 'rest', 'relaxation', 'meditation',
    'mental health', 'emotional', 'psychological',
    'pregnancy', 'pregnant', 'childbirth', 'labor', 'delivery',
    'breastfeeding', 'lactation', 'infant', 'baby', 'child',
    'elderly', 'senior', 'aging', 'geriatric',
    
    # Caregiving
    'caregiver', 'caregiving', 'caretaker', 'nurse',
    'support', 'assistance', 'help', 'aid',
    'home care', 'hospice', 'palliative', 'rehab', 'recovery',
    
    # Prevention
    'prevention', 'prevent', 'avoid', 'risk', 'safety',
    'hygiene', 'wash hands', 'mask', 'sanitize',
    'quarantine', 'isolation', 'social distancing',
    
    # Additional Diseases
    'monkeypox', 'hand foot mouth', 'kawasaki', 'scarlet fever',
    'gastritis', 'ulcer', 'ibs', 'crohn', 'colitis',
    'kidney stone', 'uti', 'urinary', 'eczema', 'psoriasis',
    'acne', 'skin cancer', 'melanoma', 'thyroid', 'hyperthyroid',
    'hypothyroid', 'goiter', 'anemia', 'hemophilia', 'leukemia',
    'lymphoma', 'glaucoma', 'cataract', 'conjunctivitis',
    'meningitis', 'encephalitis', 'sepsis',
    'stroke', 'heart attack', 'cardiac', 'angina'
]

def is_health_related(query):
    query_lower = query.lower()
    for keyword in HEALTH_KEYWORDS:
        if keyword in query_lower:
            return True
    return False

def run_gemini_with_retry(user_input, age_group="All Ages", language="English", max_retries=3):
    for attempt in range(max_retries):
        try:
            return run_gemini(user_input, age_group, language)
        except Exception as e:
            if attempt == max_retries - 1:
                return f"""
⚠️ Sorry, I couldn't process your request.

Error: {str(e)}

Please try:
1. Refreshing the page
2. Clearing chat history
3. Rephrasing your question
"""
            import time
            time.sleep(2 ** attempt)
    return "Unable to process your request."

def run_gemini(user_input, age_group="All Ages", language="English"):
    try:
        # Check cache
        cached_response = cache.get(user_input, age_group, language)
        if cached_response:
            print("✅ Using cached response")
            return cached_response
        
        # Check if health-related
        if not is_health_related(user_input):
            return f"""I'm a health education assistant focused on providing information about symptoms, diseases, and health conditions.

Your question: "{user_input}"

Please ask a health-related question such as:
- "What is diabetes?"
- "Symptoms of high blood pressure"
- "Arthritis pain relief"
- "What is measles?"
- "What is food poisoning?"
- "What is hair loss?"
- "What is memory loss?"
- "What is dizziness?"

⚠️ Educational only. Consult a doctor for medical advice."""

        # Language instructions
        lang_instructions = {
            "English": "Respond in English",
            "Urdu": "Urdu language (اردو) - use Urdu script",
            "Hindi": "Hindi language (हिंदी) - use Devanagari script",
            "Spanish": "Spanish language",
            "French": "French language",
            "Arabic": "Arabic language (العربية) - use Arabic script"
        }
        
        lang_instruction = lang_instructions.get(language, "Respond in English")
        
        prompt = f"""You are a Health Education Assistant.

USER QUESTION: {user_input}
TARGET AGE GROUP: {age_group}
LANGUAGE: {language}
INSTRUCTION: {lang_instruction}

Provide comprehensive, educational health information for this age group in the specified language:

## 📋 Overview
[Clear description of the condition/symptom]

## 🔍 How This Affects {age_group}
[Specific impacts for this age group]

## ⚠️ Signs to Watch For in {age_group}
[Age-specific symptoms]

## 🏠 Self-Care Tips for {age_group}
[Practical, age-appropriate advice]

## 🚨 When to Seek Medical Care for {age_group}
[Age-specific red flags]

## 💡 Prevention Tips for {age_group}
[Age-appropriate prevention]

---
⚠️ **Medical Disclaimer:** This is educational information only. Always consult a healthcare professional for medical advice, diagnosis, or treatment."""

        print(f"Sending request to Gemini...")
        
        response = model.generate_content(prompt)
        result = response.text
        
        # Save to cache
        cache.set(user_input, age_group, language, result)
        
        print("Response received!")
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"