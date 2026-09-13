
"""
Health Agent - Agentic AI Orchestration Layer

Architecture:

User
  ↓
app.py
  ↓
HealthAgent
  ↓
Intent Detection
  ↓
Safety Check
  ↓
Gemini Layer
  ↓
Response

This layer decides how a health question
should be handled before sending it to Gemini.
"""

from gemini_agent import run_gemini_with_retry


class HealthAgent:
    """
    Main orchestration agent for the Symptom Education Assistant.
    """

    def __init__(self):
        self.name = "Symptom Education Health Agent"

    # ========================================================
    # INTENT DETECTION
    # ========================================================

    def detect_intent(self, user_input):
        """
        Detect the basic intent of the user's question.

        Returns:
            emergency
            symptom_education
            prevention
            lifestyle
            general_health
        """

        text = user_input.lower().strip()

        # ====================================================
        # EMERGENCY INTENT
        # ====================================================

        emergency_keywords = [
            "severe chest pain",
            "chest pain",
            "difficulty breathing",
            "can't breathe",
            "cannot breathe",
            "shortness of breath",
            "unconscious",
            "passed out",
            "severe bleeding",
            "heavy bleeding",
            "stroke",
            "seizure",
            "heart attack",
            "loss of consciousness",
        ]

        for keyword in emergency_keywords:
            if keyword in text:
                return "emergency"

        # ====================================================
        # SYMPTOM EDUCATION
        # ====================================================

        symptom_keywords = [
            "symptom",
            "symptoms",
            "headache",
            "fever",
            "cough",
            "cold",
            "flu",
            "pain",
            "dizziness",
            "nausea",
            "vomiting",
            "diarrhea",
            "fatigue",
            "weakness",
            "rash",
            "swelling",
        ]

        for keyword in symptom_keywords:
            if keyword in text:
                return "symptom_education"

        # ====================================================
        # PREVENTION
        # ====================================================

        prevention_keywords = [
            "prevent",
            "prevention",
            "avoid",
            "protect",
            "how to stay healthy",
            "reduce risk",
        ]

        for keyword in prevention_keywords:
            if keyword in text:
                return "prevention"

        # ====================================================
        # LIFESTYLE
        # ====================================================

        lifestyle_keywords = [
            "diet",
            "nutrition",
            "exercise",
            "workout",
            "fitness",
            "sleep",
            "hydration",
            "water",
            "healthy lifestyle",
            "healthy food",
            "healthy foods",
            "food",
            "foods",
            "eat",
            "eating",
        ]

        for keyword in lifestyle_keywords:
            if keyword in text:
                return "lifestyle"

        # ====================================================
        # GENERAL HEALTH
        # ====================================================

        return "general_health"

    # ========================================================
    # EMERGENCY SAFETY CHECK
    # ========================================================

    def is_emergency(self, intent):
        """
        Check whether the detected intent is an emergency.
        """

        return intent == "emergency"

    # ========================================================
    # MAIN AGENT RUN METHOD
    # ========================================================

    def run(
        self,
        user_input,
        age_group="All Ages",
        language="English",
        conversation_history=None,
    ):
        """
        Main method used by the Streamlit application.
        """

        if conversation_history is None:
            conversation_history = []

        print("\n========================================")
        print("🤖 HEALTH AGENT")
        print("========================================")

        print(f"📝 User Input: {user_input}")

        # Detect intent
        intent = self.detect_intent(user_input)

        print(f"🔎 Detected Intent: {intent}")

        # ====================================================
        # EMERGENCY HANDLING
        # ====================================================

        if self.is_emergency(intent):

            print("🚨 Emergency intent detected")

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

"""

            user_input = (
                emergency_prefix
                + "\nUSER QUESTION:\n"
                + user_input
            )

        # ====================================================
        # SEND TO GEMINI
        # ====================================================

        print("🧠 Sending request to Gemini...")

        response = run_gemini_with_retry(
            user_input=user_input,
            age_group=age_group,
            language=language,
            conversation_history=conversation_history,
        )

        print("✅ Health Agent completed the request.")
        print("========================================\n")

        return response


# ============================================================
# DIRECT TESTING
# ============================================================

if __name__ == "__main__":

    agent = HealthAgent()

    test_questions = [
        "What are symptoms of flu?",
        "How can I prevent diabetes?",
        "What foods are healthy?",
        "I have severe chest pain and difficulty breathing.",
    ]

    for question in test_questions:

        print("\n----------------------------------------")
        print(f"QUESTION: {question}")
        print("----------------------------------------")

        intent = agent.detect_intent(question)

        print(f"Detected intent: {intent}")

