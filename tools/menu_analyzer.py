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
        f'"{search_query}" ingredients label MSG allergy',
        f'"{search_query}" {location} (MSG OR "yeast extract" OR allergy) reviews'
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
    Condition 1 (Restaurant Context): If the user searched for a Restaurant, you MUST output an exhaustive minimum of 15-20 realistic menu items. Do NOT just list dangerous dishes. Deliberately seek out "borderline" or simple dishes (like steamed veggies) so the user possesses a massive playbook of "Proceed With Caution" options to negotiate with the server.
    Condition 2 (Grocery Product Context): If the user searched for a specific consumer grocery product or brand (like Doritos, Ketchup, a soup can, etc.), analyze that specific product heavily. DO NOT invent a 15-item menu. Instead, output 4-5 results total: the main product they searched, followed immediately by 3-4 Alternative Brand options or Flavor Variants (e.g. if they searched Cool Ranch, output Nacho Cheese, or a safe alternative brand) so they have safe options while grocery shopping.
    
    CRITICAL BEHAVIORAL RULES:
    1. STRICTNESS: Bias heavily toward "UNKNOWN (Proceed With Caution)". 90% of restaurant savory sauces, dry rubs, and soups use commercial buckets containing Yeast Extract.
    2. THE SCRATCH-MADE RULE: Unless explicitly confirmed as a high-end scratch kitchen, assume sauces/rubs are pre-packaged.
    3. THE RESEARCH LOG (PROOF OF WORK): For every single dish, write a technical but readable 'research_log' to prove your work. CRITICAL: NEVER use the word "Tier" or "Tiers" in your output (e.g., do not say "No Tier 1 ingredients detected"). Instead, use terms like "highly-probable hidden MSG aliases" or "known commercial bases". Explicitly state exactly which chemical aliases were cross-referenced (e.g. "Natural Flavors") and what specific scraping observations led to the conclusion. Make it clear and reassuring for the average consumer.
    4. You must respond with valid JSON matching the exact schema.
    
    OUTPUT SCHEMA:
    {
      "telemetry": {
        "chars_scraped": <integer value of total chars>,
        "urls_crawled": <integer value of urls crawled>,
        "chemicals_checked": 32
      },
      "restaurant": {
        "name": "<restaurant_name>",
        "search_context": "<brief summary of the Deep Scrape findings regarding their ingredient sourcing>"
      },
      "results": [
        {
          "dish_name": "<name>",
          "status": "SAFE" | "UNSAFE" | "UNKNOWN",
          "flagged_by": ["MSG Scanner"],
          "research_log": "<Highly technical explanation of the matrix sweep and alias checks performed for this dish>",
          "confidence": "HIGH" | "LOW"
        }
      ],
      "disclaimer": "This analysis is AI-generated using Deep Web Scraping and NOT a medical guarantee. Hidden MSG and third-party sauces change constantly."
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
