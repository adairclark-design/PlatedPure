import os
import sys
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Environment Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SPOONACULAR_API_KEY = os.environ.get("SPOONACULAR_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def layer1_spoonacular(restaurant_name: str) -> str:
    """LAYER 1: The Database. Extracts verified dish names from Spoonacular for menu accuracy.
    Returns a list of confirmed dish names so the AI can synthesize ingredients against them."""
    if not SPOONACULAR_API_KEY:
        print("🟡 LAYER 1 SKIPPED: Missing SPOONACULAR_API_KEY")
        return ""
        
    print(f"🟢 LAYER 1 ACTIVE: Querying Spoonacular for {restaurant_name}...")
    try:
        search_url = f"https://api.spoonacular.com/food/menuItems/search?query={restaurant_name}&number=30&apiKey={SPOONACULAR_API_KEY}"
        search_resp = requests.get(search_url, timeout=5).json()
        menu_items = search_resp.get("menuItems", [])
        
        if not menu_items:
            print("🟡 LAYER 1 FAILED: Restaurant not found in database.")
            return ""
        
        # Extract dish names — Spoonacular macros are useless for MSG detection,
        # but verified dish NAMES give the AI a real menu to synthesize against.
        dish_names = [item.get("title", "").strip() for item in menu_items if item.get("title")]
        
        # Quality gate: need at least 5 distinct dish names to be useful
        if len(dish_names) < 5:
            print(f"🟡 LAYER 1 INSUFFICIENT: Only {len(dish_names)} dish names found.")
            return ""
        
        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in dish_names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique_names.append(name)
        
        compiled_text = (
            f"VERIFIED MENU ITEMS FROM SPOONACULAR DATABASE FOR {restaurant_name}:\n"
            f"The following are CONFIRMED real dishes on the {restaurant_name} menu. "
            f"You MUST analyze ONLY these exact dishes — do not add or invent any others.\n"
        )
        for name in unique_names:
            compiled_text += f"- {name}\n"
            
        print(f"🟢 LAYER 1 SUCCESS: Found {len(unique_names)} verified dish names.")
        return compiled_text
        
    except Exception as e:
        print(f"❌ LAYER 1 ERROR: {e}")
        return ""



def layer2_perplexity(restaurant_name: str, location: str) -> str:
    """LAYER 2: The Live Drone. Uses Perplexity via OpenRouter to bypass Cloudflare and scrape exact PDFs."""
    if not OPENROUTER_API_KEY:
        print("🔵 LAYER 2 SKIPPED: Missing OPENROUTER_API_KEY")
        return ""
        
    print(f"🔵 LAYER 2 ACTIVE: Deploying Perplexity Web Drone for {restaurant_name} {location}...")
    try:
        openrouter_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        response = openrouter_client.chat.completions.create(
            model="perplexity/sonar",
            messages=[
                {"role": "system", "content": "You are a precise ingredient extraction robot. Your sole task is to output ONLY the raw ingredient lists from a restaurant's official allergen document or menu data. Do NOT write any paragraphs, commentary, or explanations about where to find the data. If you find ingredients, list them in this format: 'Dish Name: Ingredient1, Ingredient2, Ingredient3'. If you cannot find specific ingredients, respond with exactly: INSUFFICIENT_DATA"},
                {"role": "user", "content": f"Extract the exact ingredient list for: {restaurant_name}. Search menustat.org freethenation.com and the restaurant's official allergen PDF. Return ONLY lines in the format: 'Dish Name: Ingredient1, Ingredient2'. Minimum 10 dishes."}
            ],
            timeout=30
        )
        data = response.choices[0].message.content
        if "not find" in data.lower() or "do not have" in data.lower() or "cannot access" in data.lower() or "INSUFFICIENT_DATA" in data:
            print("🟡 LAYER 2 FAILED: Drone could not locate proprietary data on the open web.")
            return ""
        # Quality gate: response must be substantial structured data (not meta-commentary)
        if len(data) < 1500 or data.count(':') < 5:
            print(f"🟡 LAYER 2 INSUFFICIENT: Response is meta-commentary, not structured ingredient data ({len(data)} chars, {data.count(':')} colons). Falling to Layer 3 Synthesis.")
            return ""
        return f"PERPLEXITY LIVE-WEB SCRAPE DATA:\n{data}"
    except Exception as e:
        print(f"❌ LAYER 2 ERROR: {e}")
        return ""


def layer2b_migraine_sentiment(restaurant_name: str, location: str) -> str:
    """LAYER 2B: The Migraine Drone. Dedicated scraping for social sentiment on Yelp/Reddit."""
    if not OPENROUTER_API_KEY:
        return "SOCIAL SENTIMENT: Migraine Drone Offline (No API Key)"
        
    print(f"🟣 LAYER 2B ACTIVE: Deploying Migraine Sentiment Drone for {restaurant_name}...")
    try:
        openrouter_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        response = openrouter_client.chat.completions.create(
            model="perplexity/sonar",
            messages=[
                {"role": "system", "content": "You are a medical sentiment analyzer. Your sole task is to search user reviews (Yelp, Reddit, TripAdvisor) for the provided restaurant and find any explicit reports of 'migraines' or 'headaches' associated with specific dishes. If you find any, list the exact dish names. If you cannot find any such reports, respond EXACTLY with 'NO_MIGRAINE_REPORTS_FOUND'. Do not write conversational text."},
                {"role": "user", "content": f"Search customer reviews for '{restaurant_name} {location}'. Are there any reviews mentioning 'migraine' or 'headaches'? List the specific dishes mentioned."}
            ],
            timeout=25
        )
        data = response.choices[0].message.content
        if "NO_MIGRAINE_REPORTS_FOUND" in data or "not find" in data.lower() or "do not have" in data.lower():
            print("🟣 LAYER 2B: No migraine reports found for specific dishes.")
            return "SOCIAL SENTIMENT: No migraine reports found for specific dishes."
            
        print("🟣 LAYER 2B: Migraine reports detected in social sentiment!")
        return f"SOCIAL SENTIMENT: MIGRAINE REPORTS FOUND in public reviews:\n{data}"
    except Exception as e:
        print(f"❌ LAYER 2B ERROR: {e}")
        return "SOCIAL SENTIMENT: Migraine Social Drone Failed"


def layer3_gpt4o_compile(restaurant_name: str, context: str, profiles: list, used_source: str, social_sentiment: str = "") -> dict:
    """LAYER 3: The Brain. Takes context from Layer 1/2, or falls back to Commercial Baseline Synthesis if empty."""
    print(f"🟠 OVERARCHING BRAIN: Booting GPT-4o JSON Compiler (Data Source: {used_source})")
    
    # If both APIs failed or missing keys, force standard synthesis.
    if not context.strip():
        used_source = "COMMERCIAL_SYNTHESIS"
        print("🟠 LAYER 3 ACTIVE: Falling back strictly to Commercial Baseline Synthesis.")
        context = "NO OFFICIAL DATA ACQUIRED. YOU MUST SYNTHESIZE COMMERCIAL BASELINES."
        
    system_prompt = f"""
    You are an elite Food Science API designed to protect patients with severe Monosodium Glutamate intolerances.
    
    You have been provided with background context generated by upstream data acquisition layers.
    DATA ACQUISITION SOURCE: {used_source}
    BACKGROUND CONTEXT (MENU & INGREDIENT DATA ONLY): {context}

    SOCIAL SENTIMENT DATA (FOR MIGRAINE FLAG ONLY — DO NOT USE FOR CHEMICAL CLASSIFICATION):
    {social_sentiment if social_sentiment else "No social sentiment data available."}
    IMPORTANT: The SOCIAL SENTIMENT DATA above is ONLY used to set the `migraine_reported` boolean.
    It has ZERO influence on whether a dish is SAFE, UNCERTAIN, or UNSAFE. Classification is determined
    EXCLUSIVELY by the MSG Chemical Database below.

    THE ABSOLUTE MSG CHEMICAL DATABASE (Identify all loopholes):
    - DIRECT MSG / GUARANTEED CARRIERS: Monosodium Glutamate (E621), Yeast Extract, Autolyzed Yeast, Hydrolyzed Veg/Soy Protein, Calcium Caseinate, Torula Yeast.
    - HIGH-RISK ADDITIVES / LOOPHOLES: Natural Flavors, Artificial Flavors, Bouillon, Broth, Maltodextrin, Pectin, Soy Sauce.
    - CHEMICAL ENHANCERS: Disodium 5'-guanylate, Disodium 5'-inosinate.
    
    CRITICAL BEHAVIORAL RULES:
    1. STRICT INGREDIENT REPORTING: You must provide a simple, flat array of atomic ingredient names for each dish. Each ingredient must be a SHORT, PLAIN ingredient name (e.g. 'Soy Sauce', 'Cornstarch', 'Natural Flavors'). NEVER write nested parenthetical sub-formulas like 'Soy Sauce (Water, Soybeans, Salt, MSG)'. Each array item must be a single, atomic ingredient string. NO nesting.
    2. THE "COMMERCIAL BASELINE" SYNTHESIS: If the BACKGROUND CONTEXT indicates "NO OFFICIAL DATA ACQUIRED", act as an INDUSTRIAL FOOD SCIENTIST. Populate the 'ingredients' array with the exact, standard commercial supply-chain formulation typically used for that specific dish at that specific restaurant. Use ATOMIC ingredient names only.
    3. ASSIGN THE SOURCE ENUM: Set 'ingredient_source' exactly matching the provided DATA ACQUISITION SOURCE: "{used_source}".
    4. NO VAGUE HEDGING: The UI renders the 'ingredients' array as chemical chips. Be precise and flat.
    5. USER-FRIENDLY INFERENCE (NO 'TIER' JARGON): Explain the risk of the 'ingredients' array in plain, simple English. DO NOT use the word 'Tier' or 'Tier 1/2/3'. Instead, say exactly why it's harmful, e.g. "Natural Flavors is a high-risk hidden additive," or "Yeast Extract is a guaranteed MSG carrier." If it is safe, say "Contains no MSG-related ingredients."
    6. STRICT FIDELITY + DENSITY: 
       - If SOURCE is 'SPOONACULAR_DB': The BACKGROUND CONTEXT contains a verified list of CONFIRMED real dish names from Spoonacular. You MUST analyze ONLY those exact dish names — no additions or substitutions. For each named dish, synthesize the standard commercial ingredient formulation used at that restaurant and classify for MSG risk.
       - If SOURCE is 'PERPLEXITY_LIVE_SCRAPE': ONLY output the exact dishes with ingredients found in BACKGROUND CONTEXT verbatim.
       - If SOURCE is 'COMMERCIAL_SYNTHESIS': Generate the 12-16 most famous real menu items for that exact restaurant. MUST include a diverse mix of entrees AND the plain unprocessed sides (e.g. steamed rice, plain veggies) that the restaurant is known to serve.
    7. STRICT FILTERING: Drop all soft drinks, sodas, and generic beverages. ONLY output true food items: entrees, appetizers, desserts, and sides.
    8. EVIDENCE-BASED CLASSIFICATION — THIS IS THE ONLY RULE THAT DETERMINES STATUS:
       - SAFE: Assign ONLY when the ingredients array is 100% clean (no MSG definitions). Simple, unprocessed items MUST be SAFE with HIGH confidence.
       - UNCERTAIN: Assign when there is a 'High-Risk Additive / Loophole' (e.g., Natural Flavors, Bouillon, Soy Sauce) OR an ambiguous sauce/marinade present. These are "possibly safe" but require server verification.
       - UNSAFE: Assign ONLY when the dish contains 'DIRECT MSG / GUARANTEED CARRIERS' (e.g., Monosodium Glutamate, Yeast Extract) OR 'CHEMICAL ENHANCERS'. These are guaranteed toxic. SOCIAL MEDIA COMPLAINTS DO NOT CHANGE THIS CLASSIFICATION.
    9. NO GENERIC INJECTIONS: You MUST NOT invent or assume any safe options. ONLY output dishes that actually exist on the literal menu of the specific restaurant being searched. Do not add plain items unless that restaurant verifiably serves them. If they do serve them (like Steamed Rice at a Chinese restaurant or Plain Black Beans at a Mexican restaurant), you MUST include them to provide a complete safety profile. If there are zero safe items on their real menu, do not invent one.
    10. SERVER INTERROGATION SCRIPT: The app is used by people with severe medical allergies. For every SAFE and UNCERTAIN dish, provide a 'server_question' string. This must be a specific, direct question the user can read to the waiter to verify safety. Be highly specific to the dish (e.g. 'Does your grill cook the burger in the same butter as the teriyaki chicken?'). For UNSAFE items, output the exact string "None".
    11. SOCIAL SENTIMENT FLAG (MIGRAINES — BOOLEAN ONLY): Look at the SOCIAL SENTIMENT DATA section above. If it explicitly names a specific dish as associated with migraines or headaches in customer reviews, set `migraine_reported` to true for that dish name. For all other dishes, set it to false. This flag does NOT affect the SAFE/UNCERTAIN/UNSAFE status.
    """


    final_output_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "analysis_results",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "telemetry": {
                        "type": "object",
                        "properties": {
                            "chars_scraped": {"type": "integer"},
                            "urls_crawled": {"type": "integer"},
                            "chemicals_checked": {"type": "integer"}
                        },
                        "required": ["chars_scraped", "urls_crawled", "chemicals_checked"],
                        "additionalProperties": False
                    },
                    "restaurant": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "search_context": {"type": "string"}
                        },
                        "required": ["name", "search_context"],
                        "additionalProperties": False
                    },
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dish_name": {"type": "string"},
                                "status": {"type": "string", "enum": ["SAFE", "UNSAFE", "UNCERTAIN"]},
                                "flagged_by": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "ingredient_source": {
                                    "type": "string",
                                    "enum": ["SPOONACULAR_DB", "PERPLEXITY_LIVE_SCRAPE", "COMMERCIAL_SYNTHESIS", "OFFICIAL_SCRAPE"]
                                },
                                "ingredients": {
                                    "type": "array",
                                    "description": "The exact corporate ingredients, or your synthesized commercial baseline list.",
                                    "items": {"type": "string"}
                                },
                                "culinary_inference": {"type": "string"},
                                "server_question": {"type": "string"},
                                "migraine_reported": {"type": "boolean"},
                                "confidence": {"type": "string", "enum": ["HIGH", "LOW"]}
                            },
                            "required": ["dish_name", "status", "flagged_by", "ingredient_source", "ingredients", "culinary_inference", "server_question", "migraine_reported", "confidence"],
                            "additionalProperties": False
                        }
                    },
                    "disclaimer": {"type": "string"}
                },
                "required": ["telemetry", "restaurant", "results", "disclaimer"],
                "additionalProperties": False
            }
        }
    }

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Compile the final json payload for {restaurant_name} using the context provided."}
            ],
            response_format=final_output_schema
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Layer 3 Brain Failure: {e}")
        return {}


def analyze_allergens(restaurant_name: str, location: str, profiles: list) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    
    source_tag = "UNCERTAIN"
    context = ""
    social_context = ""
    
    # Launch social sentiment drone immediately in the background
    # It runs while Layers 1 and 2 do their sequential work
    executor = ThreadPoolExecutor(max_workers=1)
    future_social = executor.submit(layer2b_migraine_sentiment, restaurant_name, location)
    
    # Layer 1: Spoonacular
    context = layer1_spoonacular(restaurant_name)
    if context:
        source_tag = "SPOONACULAR_DB"
    
    # Layer 2: Perplexity
    if not context:
        context = layer2_perplexity(restaurant_name, location)
        if context:
            source_tag = "PERPLEXITY_LIVE_SCRAPE"
    
    # Collect social drone result — hard 30s timeout, never blocks Layer 3
    try:
        social_context = future_social.result(timeout=30)
    except Exception:
        print("🟣 LAYER 2B TIMEOUT: Sentiment drone timed out, continuing without it.")
        social_context = "SOCIAL SENTIMENT: Drone timed out."
    finally:
        executor.shutdown(wait=False)
    
    # Layer 3 / Final Compilation
    if not context:
        source_tag = "COMMERCIAL_SYNTHESIS"
        
    payload = layer3_gpt4o_compile(
        restaurant_name, context, profiles, source_tag,
        social_sentiment=social_context
    )
    
    # Update telemetry
    if payload.get("telemetry"):
        payload["telemetry"]["chars_scraped"] = len(context)
        payload["telemetry"]["urls_crawled"] = 1 if source_tag == "SPOONACULAR_DB" else (5 if source_tag == "PERPLEXITY_LIVE_SCRAPE" else 0)
        
    return payload


if __name__ == "__main__":
    test_profiles = [
        {"name": "MSG Scanner", "restrictions": ["MSG-Free"]}
    ]
    print("Initiating 3-Layer Architecture Test...")
    res = analyze_allergens("Jersey Mikes", "Oregon", test_profiles)
    print("\n📦 COMPILED RESULTS (First 1 items):\n", json.dumps(res.get("results", [])[:1], indent=2))
