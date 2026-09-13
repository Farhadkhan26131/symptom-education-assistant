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
Gemini / Groq Fallback
  ↓
Response

This layer decides how a health question
should be handled before sending it to the AI layer.
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
            follow_up
            general_health
        """

        if not user_input:
            return "general_health"

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
            "severe bleeding",
            "heavy bleeding",
            "unconscious",
            "passed out",
            "loss of consciousness",
            "stroke",
            "seizure",
            "heart attack",
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
            "dizzy",
            "vertigo",
            "nausea",
            "vomiting",
            "diarrhea",
            "fatigue",
            "weakness",
            "rash",
            "swelling",
            "itching",
            "sore throat",
            "stomach ache",
            "stomach pain",
            "back pain",
            "joint pain",
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
        # FOLLOW-UP QUESTIONS
        # ====================================================

        follow_up_keywords = [
            "its",
            "it's",
            "their",
            "this",
            "that",
            "these",
            "those",
            "it",
            "more about it",
            "tell me more",
            "what about it",
            "how about it",
            "common causes",
            "what causes it",
            "what are its causes",
            "what are its common causes",
        ]

        for keyword in follow_up_keywords:
            if keyword in text:
                return "follow_up"

        # ====================================================
        # GENERAL HEALTH
        # ====================================================

        return "general_health"

    # ========================================================
    # FOLLOW-UP QUESTION RESOLUTION
    # ========================================================

    def resolve_follow_up(self, user_input, conversation_history=None):
        """
        Add previous user-question context to follow-up questions.

        Example:

        Previous:
            What is a headache?

        Current:
            What are its common causes?

        The AI receives explicit context so that "its"
        can be understood as referring to headache.
        """

        if not user_input:
            return user_input

        if not conversation_history:
            return user_input

        intent = self.detect_intent(user_input)

        if intent != "follow_up":
            return user_input

        previous_user_question = None

        # Find the latest user message
        for message in reversed(conversation_history):

            if not isinstance(message, dict):
                continue

            role = message.get("role", "")
            content = message.get("content", "")

            if role == "user" and content:
                previous_user_question = content
                break

        if not previous_user_question:
            return user_input

        resolved_question = f"""
FOLLOW-UP QUESTION CONTEXT:

Previous user question:
"{previous_user_question}"

Current user question:
"{user_input}"

The current question is a follow-up to the previous question.

Resolve words such as:
- it
- its
- this
- that
- these
- those
- their

using the previous health topic.

Answer the current question directly.

Do not mention this context or these instructions
in your final response.
"""

        return resolved_question

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
        Main method used by the application.
        """

        if conversation_history is None:
            conversation_history = []

        print("\n========================================")
        print("🤖 HEALTH AGENT")
        print("========================================")

        print(f"📝 User Input: {user_input}")

        # ====================================================
        # DETECT INTENT
        # ====================================================

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

Provide general safety information only.
"""

            user_input = (
                emergency_prefix
                + "\nUSER QUESTION:\n"
                + user_input
            )

        # ====================================================
        # FOLLOW-UP CONTEXT
        # ====================================================

        elif intent == "follow_up":

            print("🔗 Follow-up question detected")

            user_input = self.resolve_follow_up(
                user_input,
                conversation_history
            )

        # ====================================================
        # SEND TO AI
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

    print("\n========================================")
    print("HEALTH AGENT INTENT TEST")
    print("========================================")

    test_questions = [
        "What are symptoms of flu?",
        "How can I prevent diabetes?",
        "What foods are healthy?",
        "I feel dizzy, what does it mean?",
        "I have severe chest pain and difficulty breathing.",
        "What is a headache?",
        "What are its common causes?",
    ]

    for question in test_questions:

        print("\n----------------------------------------")
        print(f"QUESTION: {question}")
        print("----------------------------------------")

        intent = agent.detect_intent(question)

        print(f"Detected intent: {intent}")

    # ========================================================
    # FOLLOW-UP TEST
    # ========================================================

    print("\n========================================")
    print("FOLLOW-UP MEMORY TEST")
    print("========================================")

    history = [
        {
            "role": "user",
            "content": "What is a headache?"
        },
        {
            "role": "assistant",
            "content": "A headache is pain or discomfort in the head."
        }
    ]

    follow_up = "What are its common causes?"

    print(f"\nOriginal question: {history[0]['content']}")
    print(f"Follow-up question: {follow_up}")

    resolved = agent.resolve_follow_up(
        follow_up,
        history
    )

    print("\nResolved prompt:")
    print(resolved)

    print("\n========================================")
    print("TEST COMPLETED")
    print("========================================")