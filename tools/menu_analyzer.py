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
    """LAYER 1: The Database. Instant, mathematically precise ingredient arrays."""
    if not SPOONACULAR_API_KEY:
        print("🟡 LAYER 1 SKIPPED: Missing SPOONACULAR_API_KEY")
        return ""
        
    print(f"🟢 LAYER 1 ACTIVE: Querying Spoonacular for {restaurant_name}...")
    try:
        # Step 1: Search for the restaurant menu items (increased to 25 to grab actual entrees)
        search_url = f"https://api.spoonacular.com/food/menuItems/search?query={restaurant_name}&number=25&apiKey={SPOONACULAR_API_KEY}"
        search_resp = requests.get(search_url, timeout=5).json()
        menu_items = search_resp.get("menuItems", [])
        
        if not menu_items:
            print("🟡 LAYER 1 FAILED: Restaurant not found in database.")
            return ""
            
        compiled_text = f"SPOONACULAR OFFICIAL DATA FOR {restaurant_name}:\n"
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_item_info(item):
            try:
                item_id = item.get("id")
                info_url = f"https://api.spoonacular.com/food/menuItems/{item_id}?apiKey={SPOONACULAR_API_KEY}"
                info_resp = requests.get(info_url, timeout=5).json()
                nutrition_context = json.dumps(info_resp.get('nutrition', {})) 
                return f"- Dish: {item.get('title')} | Macros: {nutrition_context}\n"
            except Exception:
                return ""
                
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_item_info, item) for item in menu_items]
            for future in as_completed(futures):
                compiled_text += future.result()
            
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


def layer3_gpt4o_compile(restaurant_name: str, context: str, profiles: list, used_source: str) -> dict:
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
    BACKGROUND CONTEXT: {context}

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
    6. STRICT FIDELITY + DENSITY: If SOURCE is 'SPOONACULAR_DB' or 'PERPLEXITY_LIVE_SCRAPE', ONLY output the exact dishes from BACKGROUND CONTEXT. If SOURCE is 'COMMERCIAL_SYNTHESIS', generate the 12-16 most famous, real menu items for that exact restaurant. You MUST ensure a diverse mix: include flagship entrees, but you MUST also explicitly include the plain, unprocessed side dishes (e.g., steamed rice, plain baked potatoes, steamed vegetables) that the restaurant is known to serve.
    7. STRICT FILTERING: Drop all soft drinks, sodas, and generic beverages. ONLY output true food items: entrees, appetizers, desserts, and sides.
    8. EVIDENCE-BASED CLASSIFICATION - CRITICAL RULE:
       - SAFE: Assign ONLY when the ingredients array is 100% clean (no MSG definitions). Simple, unprocessed items MUST be SAFE with HIGH confidence.
       - UNKNOWN: Assign when there is a 'High-Risk Additive / Loophole' (e.g., Natural Flavors, Bouillon, Soy Sauce) OR an ambiguous sauce/marinade present. These are "possibly safe" but require server verification.
       - UNSAFE: Assign ONLY when the dish contains 'DIRECT MSG / GUARANTEED CARRIERS' (e.g., Monosodium Glutamate, Yeast Extract) OR 'CHEMICAL ENHANCERS'. These are guaranteed toxic.
    9. NO GENERIC INJECTIONS: You MUST NOT invent or assume any safe options. ONLY output dishes that actually exist on the literal menu of the specific restaurant being searched. Do not add plain items unless that restaurant verifiably serves them. If they do serve them (like Steamed Rice at a Chinese restaurant or Plain Black Beans at a Mexican restaurant), you MUST include them to provide a complete safety profile. If there are zero safe items on their real menu, do not invent one.
    10. SERVER INTERROGATION SCRIPT: The app is used by people with severe medical allergies. For every SAFE and UNKNOWN dish, provide a 'server_question' string. This must be a specific, direct question the user can read to the waiter to verify safety. Be highly specific to the dish (e.g. 'Does your grill cook the burger in the same butter as the teriyaki chicken?'). For UNSAFE items, leave it null.
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
                                "status": {"type": "string", "enum": ["SAFE", "UNSAFE", "UNKNOWN"]},
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
                                "server_question": {"type": ["string", "null"]},
                                "confidence": {"type": "string", "enum": ["HIGH", "LOW"]}
                            },
                            "required": ["dish_name", "status", "flagged_by", "ingredient_source", "ingredients", "culinary_inference", "server_question", "confidence"],
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
    source_tag = "UNKNOWN"
    context = ""
    
    # Layer 1
    context = layer1_spoonacular(restaurant_name)
    if context:
        source_tag = "SPOONACULAR_DB"
    
    # Layer 2
    if not context:
        context = layer2_perplexity(restaurant_name, location)
        if context:
            source_tag = "PERPLEXITY_LIVE_SCRAPE"
            
    # Layer 3 / Final Compilation
    if not context:
        source_tag = "COMMERCIAL_SYNTHESIS"
        
    payload = layer3_gpt4o_compile(restaurant_name, context, profiles, source_tag)
    
    # Mock telemetry
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
