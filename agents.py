"""
Specialized Worker Agents for the Health Assistant.
Based on Module 2 (Supervisor/Worker Pattern) and Module 3 (Multi-Agent Systems).
"""

from gemini_agent import run_gemini_with_retry

class EmergencyAgent:
    """Handles life-threatening or emergency medical intents."""
    def __init__(self):
        self.name = "Emergency Safety Agent"

    def respond(self, user_input, age_group, language):
        emergency_prompt = f"""
        IMPORTANT SAFETY NOTICE:
        The user's message may describe a potentially serious or emergency medical situation.
        The response must clearly recommend seeking urgent professional medical evaluation.
        Do not attempt to diagnose the condition.
        Do not provide false reassurance.
        If symptoms are severe, worsening, or potentially life-threatening, advise the user to contact local emergency services or go to the nearest emergency medical facility immediately.
        Provide general safety information only. Do not provide medication doses.

        USER QUESTION: {user_input}
        """
        return run_gemini_with_retry(
            user_input=emergency_prompt,
            age_group=age_group,
            language=language,
            conversation_history=[],
            summary="",
            tool_result=None
        )

class SymptomEducationAgent:
    """Handles general symptom education and follow-up questions."""
    def __init__(self):
        self.name = "Symptom Education Agent"

    def respond(self, user_input, age_group, language, conversation_history):
        prompt = f"""
        HEALTH SYMPTOM QUESTION
        The user is asking about a health symptom.
        Treat this as a valid health education question.
        Provide simple, general educational information.
        Explain possible common meanings or causes without diagnosing the user.
        Include appropriate safety guidance.
        If symptoms are severe, sudden, worsening, or concerning, recommend seeking professional medical care.
        Do not diagnose the user. Do not prescribe medication. Do not provide medication doses.
        Answer the user's question directly.

        USER QUESTION: {user_input}
        """
        return run_gemini_with_retry(
            user_input=prompt,
            age_group=age_group,
            language=language,
            conversation_history=conversation_history,
            summary="",
            tool_result=None
        )

class LifestyleAgent:
    """Handles prevention, diet, exercise, and general lifestyle questions."""
    def __init__(self):
        self.name = "Lifestyle Agent"

    def respond(self, user_input, age_group, language, conversation_history):
        prompt = f"""
        LIFESTYLE AND PREVENTION QUESTION
        The user is asking about healthy habits, diet, exercise, or prevention.
        Provide general educational information about healthy lifestyle choices.
        Do not diagnose any conditions. Do not prescribe specific medical treatments.

        USER QUESTION: {user_input}
        """
        return run_gemini_with_retry(
            user_input=prompt,
            age_group=age_group,
            language=language,
            conversation_history=conversation_history,
            summary="",
            tool_result=None
        )