"""
Health Agent - First Agentic AI Layer

This file acts as the orchestration layer between
the Streamlit application and the existing Gemini layer.

Current architecture:

User
  ↓
app.py
  ↓
agent.py
  ↓
gemini_agent.py
  ↓
Gemini API
  ↓
Response

Later we will add:
- Intent detection
- Planning
- Tool selection
- Tools
- RAG
- Memory
- Safety/guardrails
"""

from gemini_agent import run_gemini_with_retry


class HealthAgent:
    """
    Main Agent for the Symptom Education Assistant.
    """

    def __init__(self):
        self.name = "Symptom Education Health Agent"

    def run(
        self,
        user_input,
        age_group="All Ages",
        language="English",
        conversation_history=None,
    ):
        """
        Process a user's health education question.

        Parameters:
            user_input (str):
                Current user question.

            age_group (str):
                Selected age group.

            language (str):
                Selected response language.

            conversation_history (list):
                Previous conversation messages.

        Returns:
            str:
                Final response from the Gemini layer.
        """

        # Make sure conversation history is always a list.
        if conversation_history is None:
            conversation_history = []

        print("🤖 Health Agent is processing the request...")

        # Send the request to the existing Gemini layer.
        response = run_gemini_with_retry(
            user_input=user_input,
            age_group=age_group,
            language=language,
            conversation_history=conversation_history,
        )

        print("✅ Health Agent received a response.")

        return response


# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":

    agent = HealthAgent()

    response = agent.run(
        user_input="What is a fever?",
        age_group="Adult",
        language="English",
        conversation_history=[],
    )

    print("\n========================================")
    print("AGENT RESPONSE")
    print("========================================")
    print(response)