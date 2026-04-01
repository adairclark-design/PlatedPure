import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = OpenAI()

def fetch_url_text(url: str, max_chars: int = 5000) -> str:
    """Attempts to download raw HTML and extract text from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return " ".join(text.split())[:max_chars]
        return ""
    except Exception:
        return ""

def fetch_restaurant_context(search_query: str, location: str) -> dict:
    """
    Deep Scrape Engine: Runs multi-vector DDGS queries for both restaurants and grocery products.
    """
    queries = [
        f'"{search_query}" "ingredients" (nutrition OR allergen OR "contains") exact list',
        f'"{search_query}" (site:menustat.org OR site:fooducate.com OR site:smartlabel.org) ingredients',
        f'"{search_query}" {location} (MSG OR "yeast extract") reviews'
    ]
    
    context_snippets = []
    urls_scraped = 0
    total_chars = 0
    
    for query in queries:
        print(f"🔍 Deep searching: {query}")
        try:
            results = list(DDGS().text(query, max_results=4))
            for res in results:
                # Always append the snippet as a baseline
                snippet_text = f"Snippet: {res.get('title')} - {res.get('body')}"
                context_snippets.append(snippet_text)
                total_chars += len(snippet_text)
                
                # Attempt physical HTML crawl if we haven't hit the limit
                url = res.get('href', '')
                if url and urls_scraped < 3:
                    html_text = fetch_url_text(url)
                    if html_text:
                        context_snippets.append(f"--- DEEP CRAWL OF {url} ---\n{html_text}\n--- END CRAWL ---")
                        total_chars += len(html_text)
                        urls_scraped += 1
        except Exception as e:
            print(f"❌ Web Search Error on '{query}': {e}")
            
    return {
        "text": "\n\n".join(context_snippets),
        "urls": urls_scraped,
        "chars": total_chars
    }

def analyze_allergens(restaurant_name: str, location: str, profiles: list) -> dict:
    """
    Combines deep scraped web context with OpenAI reasoning to build the safe/unsafe payload.
    """
    context_data = fetch_restaurant_context(restaurant_name, location)
    
    system_prompt = """
    You are an elite, specialized "MSG Detection Engine" designed to protect patients with severe Monosodium Glutamate intolerances. Your singular job is to analyze restaurant menus and flag any potential sources of MSG or its hidden aliases with pinpoint accuracy.
    
    THE ABSOLUTE MSG CHEMICAL DATABASE (Identify all loopholes):
    Restaurants NEVER list "MSG". You MUST aggressively cross-reference ingredients against these 3 Danger Tiers:
    - [TIER 1] GUARANTEED MSG (Manufactured Free Glutamate): Monosodium Glutamate (E621), Monopotassium Glutamate (E622), Calcium/Monoammonium/Magnesium/Natrium Glutamate, Autolyzed Yeast, Yeast Extract, Yeast Food, Yeast Nutrient, Torula Yeast, Hydrolyzed Vegetable/Plant/Soy/Wheat/Pea/Corn Protein, Calcium Caseinate, Sodium Caseinate, Textured Vegetable Protein, Gelatin, Vetsin, Ajinomoto.
    - [TIER 2] HIGH PROBABILITY (Formed during processing): "Natural Flavors", "Natural Chicken/Beef Flavoring", "Artificial Flavors", Bouillon, Broth, Stock, Maltodextrin, Malt Extract, Barley Malt, Carrageenan (E407), Pectin (E440), Citric Acid (E330), Soy Sauce, Soy Sauce Extract, Protease Enzymes, "Enzyme-Modified".
    - [TIER 3] ENHANCERS (Indicators MSG is present): Disodium 5'-guanylate (E627), Disodium 5'-inosinate (E631), Disodium 5'-ribonucleotides (E635).
    
    HYBRID RECONSTRUCTION COMMAND:
    Condition 1 (Restaurant Context): If the user searched for a Restaurant, fast-food chain, casual dining brand, or any place where humans eat (e.g. "Panda Express", "Olive Garden", "Chipotle", "local sushi bar"), you MUST output an exhaustive MINIMUM of 15-20 realistic menu items. Do NOT confuse a restaurant chain with a grocery product. Deliberately seek out "borderline" or simple dishes (steamed veggies, plain rice, fresh fruit) so the user has a massive playbook of "Proceed With Caution" AND genuinely SAFE options. For items that are verifiably plain, unprocessed, or have publicly confirmed ingredient lists with no MSG aliases, you MUST mark them SAFE with HIGH confidence. Do not reflexively mark everything UNKNOWN — that makes the tool useless.
    Condition 2 (Grocery Product Context): If the user searched for a specific packaged consumer product intended to be bought off a shelf (e.g. "Doritos Cool Ranch", "Heinz Ketchup", "Campbell's Chicken Noodle Soup"), analyze that specific product. DO NOT invent a 15-item menu. Instead, output 4-5 results: the searched product first, then 3-4 Alternative Brand options or Flavor Variants.
    
    CRITICAL BEHAVIORAL RULES:
    1. STRICT EVIDENCE REPORTING: For every single dish, you must now separate your analysis into two distinct fields: 'verified_ingredients' and 'culinary_inference'.
    2. VERIFIED INGREDIENTS: If and ONLY IF the deep scan returned an exact, verifiable list of ingredients for the dish, provide them as a comma-separated array of strings in 'verified_ingredients'. If the exact ingredients are NOT found in the text, this array MUST be empty []. DO NOT hallucinate ingredients into this list.
    3. CULINARY INFERENCE: Use this field to explain the risk. If you have verified ingredients, explain exactly which ones match the MSG Danger Tiers. If the 'verified_ingredients' array is empty, explicitly state "Official exact ingredients unavailable." and then explain the standard culinary preparation risks (e.g., why American-Chinese Chow Mein typically contains Soy Sauce).
    4. BALANCED STRICTNESS: Bias toward "UNKNOWN" for savory sauces, dry rubs, and soups. However, genuinely plain items (steamed rice, whole fruit, packaged items with a clean label) MUST be marked SAFE with HIGH confidence. Never mark a dish UNKNOWN just because you lack information - investigate and reason carefully based on culinary norms.
    5. Output valid JSON matching the exact schema. NEVER use the word "Tier" in your final output text.
    
    OUTPUT SCHEMA:
    {
      "telemetry": {
        "chars_scraped": <integer value of total chars>,
        "urls_crawled": <integer value of urls crawled>,
        "chemicals_checked": 32
      },
      "restaurant": {
        "name": "<restaurant_name>",
        "search_context": "<brief summary of the Deep Scrape findings regarding their ingredient sourcing and transparency>"
      },
      "results": [
        {
          "dish_name": "<name>",
          "status": "SAFE" | "UNSAFE" | "UNKNOWN",
          "flagged_by": ["MSG Scanner"],
          "verified_ingredients": ["<ingredient_1>", "<ingredient_2>"] | [],
          "culinary_inference": "<Explanation of verified ingredients, OR statement that ingredients are hidden followed by culinary risk analysis>",
          "confidence": "HIGH" | "LOW"
        }
      ],
      "disclaimer": "This analysis is an investigative guide. Unlisted ingredients and third-party commercial sauces change constantly."
    }
    """
    
    user_prompt = f"""
    Search Target: {restaurant_name} (Region Context: {location})
    Task: Identify if this is a Restaurant or Grocery Product and execute the appropriate HYBRID RECONSTRUCTION COMMAND logic.
    
    Telemetry Data:
    URLs Crawled: {context_data['urls']}
    Total Characters Extracted: {context_data['chars']}
    
    Deep Web Context (Reviews & Menus):
    {context_data['text']}
    
    Act as the MSG Detection Engine. Output the exact telemetry data provided above, reconstruct the requested items using technical research logs, and output pure JSON.
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
    
    print("🚀 Starting Additive Detective Engine...\n")
    final_payload = analyze_allergens("Bottega", "Yountville, CA", test_profiles)
    
    print("\n📦 FINAL DELIVERABLE PAYLOAD:\n")
    print(json.dumps(final_payload, indent=2))
