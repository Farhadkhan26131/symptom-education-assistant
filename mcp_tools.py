"""
MCP-compatible tool wrappers.
Based on Module 3 (Native MCP Tool Integration).
"""

from tools import search_symptom_information

def get_mcp_symptom_tool():
    """
    Returns an MCP-compatible tool definition.
    This allows the agent to dynamically discover and call this tool.
    """
    return {
        "name": "search_symptom_information",
        "description": "Search for educational health information about a symptom",
        "parameters": {
            "type": "object",
            "properties": {
                "symptom": {
                    "type": "string",
                    "description": "The symptom to search (e.g., headache, fever)"
                },
                "age_group": {
                    "type": "string",
                    "description": "Age group: Children, Teenagers, Adults, Older Adults"
                }
            },
            "required": ["symptom"]
        },
        "function": search_symptom_information
    }