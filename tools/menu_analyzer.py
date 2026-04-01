import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = OpenAI()

def fetch_restaurant_context(restaurant_name: str, location: str) -> str:
    """
    Uses DuckDuckGo to extract immediate web snippets containing menu and review data.
    """
    search_query = f'"{restaurant_name}" {location} menu reviews'
    print(f"🔍 Searching context for: {search_query}")
    
    try:
        results = DDGS().text(search_query, max_results=5)
        context_snippets = []
        for res in results:
            context_snippets.append(f"Title: {res.get('title')}\nSnippet: {res.get('body')}")
        
        return "\n\n".join(context_snippets)
    except Exception as e:
        print(f"❌ Web Search Error: {e}")
        return "No external context found."

def analyze_allergens(restaurant_name: str, location: str, profiles: list) -> dict:
    """
    Combines web snippets with OpenAI reasoning to build the safe/unsafe payload.
    """
    context = fetch_restaurant_context(restaurant_name, location)
    
    system_prompt = """
    You are an expert culinary investigator and medical safety AI. Your job is to assess menu items 
    based on the provided web context, your extensive knowledge of culinary preparation, and the "Hidden Lexicon" of deceptive ingredients.
    
    THE "HIDDEN LEXICON" (Ghost Ingredients):
    If a profile is MSG-Free, you MUST explicitly flag dishes likely to contain: Yeast Extract, Hydrolyzed Vegetable Protein, Autolyzed Yeast, Calcium Caseinate, Natural Flavorings, Torula Yeast, or third-party sauces (Soy Sauce, Bouillon, commercial Mayo, pre-made marinades). 
    If a profile is Gluten-Free, strongly flag cross-contamination in fryers and hidden flour in thickeners (roux, sauces).
    
    HYBRID RECONSTRUCTION COMMAND:
    You MUST output a minimum of 10-12 realistic menu items for this restaurant.
    1. First, analyze all dishes explicitly mentioned in the Web Context Snippets.
    2. If the snippets do not contain 10-12 items, you MUST use your vast pre-trained knowledge of this physical restaurant (or identical restaurants of this specific cuisine/location) to fill the gaps and provide a robust, comprehensive 10-12 item menu breakdown. 
    
    CRITICAL BEHAVIORAL RULES:
    1. You are an investigative assistant, NOT a medical guarantor.
    2. If an ingredient's safety is ambiguous or relies on a third-party sauce (where the chef might not know the ingredients), flag as 'UNKNOWN'.
    3. For ANY dish marked 'UNKNOWN' or 'SAFE (conditional)', you MUST provide 1-3 highly specific 'validation_questions' the user should read to their server to confirm safety. (e.g., "Is your soy sauce house-made or a commercial brand containing hydrolyzed protein?", "Does this sauce use yeast extract or bouillon powder?")
    4. You must respond with valid JSON matching the exact schema provided.
    
    OUTPUT SCHEMA:
    {
      "restaurant": {
        "name": "<restaurant_name>",
        "search_context": "<brief summary of what you found online and any general warnings>"
      },
      "results": [
        {
          "dish_name": "<name>",
          "status": "SAFE" | "UNSAFE" | "UNKNOWN",
          "flagged_by": ["ProfileName1"],
          "reasoning": "<why it is safe/unsafe, explicitly citing the Hidden Lexicon if applicable>",
          "validation_questions": ["<Question 1 for the server>", "<Question 2 for the server>"],
          "confidence": "HIGH" | "LOW"
        }
      ],
      "disclaimer": "This analysis is AI-generated and NOT a medical guarantee. Menus and third-party ingredients change constantly. Always confirm with your server using the questions provided."
    }
    """
    
    user_prompt = f"""
    Restaurant: {restaurant_name} ({location})
    Profiles: {json.dumps(profiles)}
    
    Web Context Snippets:
    {context}
    
    Analyze the menu items mentioned in the context (or that you know belong to this classic restaurant).
    Output pure JSON.
    """

    print("🧠 Analyzing context with OpenAI...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Can drop to gpt-4o-mini for extreme cost savings
            temperature=0.1, # Keep strictly deterministic and risk-averse
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Test Data mimicking the Frontend Input Payload
    test_profiles = [
        {"name": "Dad", "restrictions": ["Gluten-Free"]},
        {"name": "Mom", "restrictions": ["MSG-Free"]}
    ]
    
    print("🚀 Starting PlatedPure Zero-Cost Engine...\n")
    final_payload = analyze_allergens("Bottega", "Yountville, CA", test_profiles)
    
    print("\n📦 FINAL DELIVERABLE PAYLOAD:\n")
    print(json.dumps(final_payload, indent=2))
