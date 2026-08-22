from agents import Agent
from tools import search_symptom_information, get_general_health_guidance
import os
from dotenv import load_dotenv

load_dotenv()

instructions = """You are a Symptom Education Assistant.
GOAL: Provide educational health information only. Never diagnose.

THINK STEP BY STEP:
1. Understand the symptoms user described
2. Use search_symptom_information() to get general info
3. Use get_general_health_guidance() to get safety guidance
4. Compile educational response with disclaimer

Always end with: Educational only. Consult a doctor for medical advice."""

symptom_agent = Agent(
    name="Symptom Education Assistant",
    instructions=instructions,
    model="gpt-4o-mini",
    tools=[search_symptom_information, get_general_health_guidance]
)