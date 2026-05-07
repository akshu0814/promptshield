import os
import sys

os.environ["PROMPTSHIELD_API_URL"] = "http://localhost:8000"
sys.path.insert(0, "/Users/axu/Desktop/promptshield /sdk")

from promptshield import shield, InjectionDetected

@shield
def ask_llm(user_message: str) -> str:
    return f"[Fake LLM] You asked: {user_message}"


print("=" * 50)
print("   PromptShield — Interactive Test")
print("=" * 50)
print("Type any message and press Enter.")
print("Type 'quit' to exit.\n")

while True:
    user_input = input("You: ").strip()

    if not user_input:
        continue

    if user_input.lower() == "quit":
        print("Goodbye!")
        break

    try:
        response = ask_llm(user_input)
        print(f"LLM: {response}")

    except InjectionDetected as e:
        print(f"🚨 BLOCKED — Attack detected before reaching LLM!")
        print(f"   category : {e.category}")
        print(f"   severity : {e.severity}")
        print(f"   rule     : {e.rule}")
        print(f"   event_id : {e.event_id}")

    print()
