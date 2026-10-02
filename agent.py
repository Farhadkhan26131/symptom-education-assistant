"""
Health Agent - Agentic AI Orchestration Layer (Upgraded)

Architecture:
User -> app.py -> HealthAgent (Supervisor)
  -> Detect Intent
  -> [Scratchpad Plan - DISABLED to save API quota]
  -> Route to Worker Agent (Module 3)
  -> Groq (Primary) / Gemini (Fallback)
"""

from gemini_agent import run_gemini_with_retry
from agents import EmergencyAgent, SymptomEducationAgent, LifestyleAgent


class HealthAgent:
    """
    Main orchestration agent (Supervisor) for the Symptom Education Assistant.
    """

    def __init__(self):
        self.name = "Symptom Education Health Agent"
        # Initialize Worker Agents
        self.emergency_agent = EmergencyAgent()
        self.symptom_agent = SymptomEducationAgent()
        self.lifestyle_agent = LifestyleAgent()

    # ========================================================
    # INTENT DETECTION
    # ========================================================

    def detect_intent(self, user_input):
        """Detect the basic intent of the user's question."""
        if not user_input:
            return "general_health"

        text = user_input.lower().strip()

        # ====================================================
        # EMERGENCY INTENT
        # ====================================================
        emergency_keywords = [
            "severe chest pain", "chest pain", "difficulty breathing",
            "can't breathe", "cannot breathe", "shortness of breath",
            "severe bleeding", "heavy bleeding", "unconscious",
            "passed out", "loss of consciousness", "stroke",
            "seizure", "heart attack"
        ]
        for keyword in emergency_keywords:
            if keyword in text:
                return "emergency"

        # ====================================================
        # SYMPTOM EDUCATION
        # ====================================================
        symptom_keywords = [
            "symptom", "symptoms", "headache", "fever", "cough", "cold",
            "flu", "pain", "dizziness", "dizzy", "vertigo", "nausea",
            "vomiting", "diarrhea", "fatigue", "weakness", "rash",
            "swelling", "itching", "sore throat", "stomach ache",
            "stomach pain", "back pain", "joint pain"
        ]
        for keyword in symptom_keywords:
            if keyword in text:
                return "symptom_education"

        # ====================================================
        # PREVENTION
        # ====================================================
        prevention_keywords = [
            "prevent", "prevention", "avoid", "protect",
            "how to stay healthy", "reduce risk"
        ]
        for keyword in prevention_keywords:
            if keyword in text:
                return "prevention"

        # ====================================================
        # LIFESTYLE
        # ====================================================
        lifestyle_keywords = [
            "diet", "nutrition", "exercise", "workout", "fitness",
            "sleep", "hydration", "water", "healthy lifestyle",
            "healthy food", "healthy foods", "food", "foods",
            "eat", "eating"
        ]
        for keyword in lifestyle_keywords:
            if keyword in text:
                return "lifestyle"

        # ====================================================
        # FOLLOW-UP QUESTIONS
        # ====================================================
        follow_up_keywords = [
            "its", "it's", "their", "this", "that", "these", "those",
            "it", "more about it", "tell me more", "what about it",
            "how about it", "common causes", "what causes it",
            "what are its causes", "what are its common causes"
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
        """Add previous user-question context to follow-up questions."""
        if not user_input or not conversation_history:
            return user_input

        intent = self.detect_intent(user_input)
        if intent != "follow_up":
            return user_input

        previous_user_question = None
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

        return f"""
FOLLOW-UP QUESTION CONTEXT:
Previous user question: "{previous_user_question}"
Current user question: "{user_input}"

The current question is a follow-up to the previous question.
Resolve words such as: it, its, this, that, these, those, their using the previous health topic.
Answer the current question directly.
Do not mention this context or these instructions in your final response.
"""

    # ========================================================
    # SCRATCHPAD PLANNER (DISABLED TO SAVE API QUOTA)
    # ========================================================
    # Uncomment this method and the call inside run() if you want
    # to enable the Planner step. Note: This doubles your API usage.

    # def generate_plan(self, user_input, intent, age_group):
    #     """
    #     Scratchpad step (Module 2): Ask the AI to plan the response
    #     before generating the final answer.
    #     """
    #     plan_prompt = f"""
    #     You are a medical education planner.
    #     The user's intent is: {intent}
    #     User's age group: {age_group}
    #     User's question: {user_input}
    #
    #     List 3-4 brief steps on how to safely educate the user.
    #     Do NOT answer the user. Just output the plan.
    #     """
    #
    #     plan = run_gemini_with_retry(
    #         user_input=plan_prompt,
    #         age_group=age_group,
    #         language="English",
    #         conversation_history=[],
    #         summary="",
    #         tool_result=None
    #     )
    #     return plan

    # ========================================================
    # MAIN AGENT RUN METHOD (SUPERVISOR ROUTING)
    # ========================================================

    def run(self, user_input, age_group="All Ages", language="English", conversation_history=None):
        """Main method used by the application (Supervisor Routing)."""
        if conversation_history is None:
            conversation_history = []

        print("\n========================================")
        print("🤖 HEALTH AGENT (SUPERVISOR)")
        print("========================================")

        intent = self.detect_intent(user_input)
        print(f"🔎 Detected Intent: {intent}")

        # ====================================================
        # SCRATCHPAD PLAN - DISABLED TO SAVE API QUOTA
        # ====================================================
        # Uncomment the lines below to enable the Planner step.
        # WARNING: This doubles your API usage (2 calls per question).

        # print("🧠 Generating scratchpad plan...")
        # scratchpad_plan = self.generate_plan(user_input, intent, age_group)
        # print(f"📝 Plan: {scratchpad_plan[:100]}...")

        # ====================================================
        # ROUTE TO WORKER AGENT
        # ====================================================

        if intent == "emergency":
            print("🚨 Routing to Emergency Agent")
            return self.emergency_agent.respond(user_input, age_group, language)

        elif intent in ["symptom_education", "follow_up", "general_health"]:
            print("🩺 Routing to Symptom Education Agent")
            # Handle follow-up resolution here before sending to worker
            if intent == "follow_up":
                user_input = self.resolve_follow_up(user_input, conversation_history)
            return self.symptom_agent.respond(user_input, age_group, language, conversation_history)

        elif intent in ["prevention", "lifestyle"]:
            print("🥗 Routing to Lifestyle Agent")
            return self.lifestyle_agent.respond(user_input, age_group, language, conversation_history)

        else:
            print("🩺 Routing to Symptom Education Agent (Fallback)")
            return self.symptom_agent.respond(user_input, age_group, language, conversation_history)


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
        {"role": "user", "content": "What is a headache?"},
        {"role": "assistant", "content": "A headache is pain or discomfort in the head."}
    ]

    follow_up = "What are its common causes?"

    print(f"\nOriginal question: {history[0]['content']}")
    print(f"Follow-up question: {follow_up}")

    resolved = agent.resolve_follow_up(follow_up, history)

    print("\nResolved prompt:")
    print(resolved)

    print("\n========================================")
    print("TEST COMPLETED")
    print("========================================")