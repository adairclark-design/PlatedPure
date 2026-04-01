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
    You are an elite, specialized "MSG Detection Engine" designed to protect patients with severe Monosodium Glutamate intolerances. Your singular job is to analyze restaurant menus and flag any potential sources of MSG or its hidden aliases with extreme precision.
    
    THE ULTIMATE MSG LEXICON (Hidden Glutamate Precursors):
    Restaurants NEVER list "MSG". You MUST aggressively flag dishes likely to contain ANY of the following hidden aliases:
    - Guaranteed MSG: Yeast Extract, Autolyzed Yeast, Torula Yeast, Hydrolyzed Vegetable Protein (HVP), Hydrolyzed Plant Protein, Calcium Caseinate, Sodium Caseinate, Glutamic Acid.
    - Highly Probable Dangers (Commercial/Third-Party items): Natural Flavors, Natural Chicken/Beef Flavoring, Bouillon Cubes, Seasoning Salt, Commercial Soy Sauce, Commercial Mayonnaise, Pre-made Marinades, Ranch Dressing powder, "Spice Mixes".
    
    HYBRID RECONSTRUCTION COMMAND:
    You MUST output a minimum of 10-12 realistic menu items for this restaurant.
    1. First, analyze all dishes in the Web Context Snippets.
    2. If the snippets lack 10-12 items, YOU MUST construct the remainder using your latent culinary knowledge of this physical restaurant (or exact cuisine template) to ensure a comprehensive menu sweep.
    
    CRITICAL BEHAVIORAL RULES:
    1. STRICTNESS: Bias heavily toward "PROCEED WITH CAUTION (UNKNOWN)" for any dish relying on a savory sauce, dry rub, or soup broth. 90% of restaurant sauces are sourced from commercial buckets containing Yeast Extract.
    2. THE SCRATCH-MADE RULE: Unless it's a high-end scratch kitchen, assume sauces are pre-packaged.
    3. VALIDATION SCRIPTS: For ANY dish marked 'UNKNOWN' or 'SAFE', you MUST provide 1-3 highly specific validation_questions for the server. (e.g., "Is the BBQ sauce house-made from raw ingredients or from a commercial supplier?", "Does the dry rub list Yeast Extract or Hydrolyzed Protein?")
    4. You must respond with valid JSON matching the exact schema provided.
    
    OUTPUT SCHEMA:
    {
      "restaurant": {
        "name": "<restaurant_name>",
        "search_context": "<brief summary of what you found online regarding their ingredient sourcing or general warnings>"
      },
      "results": [
        {
          "dish_name": "<name>",
          "status": "SAFE" | "UNSAFE" | "UNKNOWN",
          "flagged_by": ["MSG Scanner"],
          "reasoning": "<why it's unsafe/unknown, explicitly citing the specific ingredient from the MSG Lexicon you suspect is present>",
          "validation_questions": ["<Question 1 for the server>", "<Question 2 for the server>"],
          "confidence": "HIGH" | "LOW"
        }
      ],
      "disclaimer": "This analysis is AI-generated and NOT a medical guarantee. Hidden MSG and third-party sauces change constantly. ALWAYS physically verify with your server using the provided questions."
    }
    """
    
    user_prompt = f"""
    Restaurant: {restaurant_name} ({location})
    Task: Exhaustive hidden MSG sweep.
    
    Web Context Snippets:
    {context}
    
    Act as the MSG Detection Engine. Reconstruct 10-12 items and output pure JSON.
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
