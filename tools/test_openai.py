import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

def test_openai_connection():
    # Load environment variables from .env file
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-...") or api_key == "":
        print("❌ ERROR: OPENAI_API_KEY is missing or invalid in .env")
        sys.exit(1)

    print("🔑 OPENAI_API_KEY found. Testing connection...")
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Use cheap model for ping
            messages=[
                {"role": "user", "content": "Ping. Reply only with 'Pong'."}
            ],
            max_tokens=5
        )
        print(f"✅ SUCCESS: OpenAI API responded correctly: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ ERROR: OpenAI API connection failed.\nDetails: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_openai_connection()
