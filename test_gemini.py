from gemini_agent import run_gemini

def test():
    print("=" * 50)
    print("Testing Symptom Agent with Gemini (FREE)")
    print("=" * 50)
    
    result = run_gemini("I have a headache and fever")
    print("\nResponse:")
    print(result)

if __name__ == "__main__":
    test()