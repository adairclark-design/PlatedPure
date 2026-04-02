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
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
openrouter_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1") if OPENROUTER_API_KEY else None

def layer1_spoonacular(restaurant_name: str) -> str:
    """LAYER 1: The Database. Extracts verified dish names from Spoonacular for menu accuracy.
    Returns a list of confirmed dish names so the AI can synthesize ingredients against them."""
    if not SPOONACULAR_API_KEY:
        print("🟡 LAYER 1 SKIPPED: Missing SPOONACULAR_API_KEY")
        return ""
        
    print(f"🟢 LAYER 1 ACTIVE: Querying Spoonacular for {restaurant_name}...")
    try:
        search_url = f"https://api.spoonacular.com/food/menuItems/search?query={restaurant_name}&number=35&apiKey={SPOONACULAR_API_KEY}"
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


def _drone_worker(restaurant_name: str, location: str, target_instructions: str, drone_name: str) -> str:
    if not OPENROUTER_API_KEY:
        return ""
    try:
        response = openrouter_client.chat.completions.create(
            model="perplexity/sonar",
            messages=[
                {"role": "system", "content": "You are a precise ingredient extraction robot. Your sole task is to output ONLY the raw ingredient lists from a restaurant's official allergen document or menu data. Return ONLY fully assembled, complete menu items (e.g., 'Big Mac', 'Quarter Pounder'). Do NOT output individual raw components, condiments, patties, or sauces like 'Mustard' or 'Lettuce'. Do NOT write any paragraphs, commentary, or explanations about where to find the data. If you find ingredients, list them in this format: 'Dish Name: Ingredient1, Ingredient2, Ingredient3'. If you cannot find specific ingredients, respond with exactly: INSUFFICIENT_DATA"},
                {"role": "user", "content": f"Extract the exact ingredient list for: {restaurant_name} located near {location}. {target_instructions} Where relevant, look for any location-specific menu items for the {location} area. Return ONLY lines in the format: 'Dish Name: Ingredient1, Ingredient2'. Minimum 20 fully assembled dishes if possible. Exclude mere condiments."}
            ],
            timeout=30
        )
        data = response.choices[0].message.content
        if "not find" in data.lower() or "do not have" in data.lower() or "INSUFFICIENT_DATA" in data:
            return ""
        return f"\n--- {drone_name} RESULTS ---\n{data}\n"
    except Exception as e:
        print(f"❌ {drone_name} ERROR: {e}")
        return ""

def layer2_perplexity(restaurant_name: str, location: str) -> str:
    """LAYER 2: Dual-Drone Pincer. Fires two simultaneous Perplexity queries at different domains."""
    from concurrent.futures import ThreadPoolExecutor

    print(f"🔵 LAYER 2 ACTIVE: Deploying Dual-Drones for {restaurant_name} {location}...")
    
    prompt_a = "CRITICAL: To bypass Cloudflare bot protection, you MUST explicitly target secondary academic and nutrition databases. Specifically search domains like menustat.org and fastfoodnutrition.org. Do NOT rely on the official restaurant homepage."
    prompt_b = "CRITICAL: To bypass Cloudflare bot protection, you MUST explicitly search for '.pdf allergen' documents and target the domain nutritionix.com. Do NOT rely on the official restaurant homepage."

    # Fire both drones concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_drone_worker, restaurant_name, location, prompt_a, "DRONE A (ACADEMIC)")
        future_b = executor.submit(_drone_worker, restaurant_name, location, prompt_b, "DRONE B (NUTRITIONIX/PDF)")
        
        result_a = future_a.result()
        result_b = future_b.result()

    combined_data = result_a + result_b
    if not combined_data.strip():
        print("🟡 LAYER 2 FAILED: Both Drones could not locate proprietary data on the open web.")
        return ""
        
    # Quality gate: response must be substantial structured data
    if len(combined_data) < 1000 or combined_data.count(':') < 5:
        print(f"🟡 LAYER 2 INSUFFICIENT: Response lacked structured ingredient data. Falling to Layer 3 Synthesis.")
        return ""
        
    return f"DUAL-DRONE PERPLEXITY DATA:\n{combined_data}"

def layer2_deep_crawl(restaurant_name: str, location: str) -> str:
    """LAYER 2 (DEEP): Uses Jina Web Search to aggressively scrape Javascript-rendered sites."""
    # We prefer Jina because it searches AND renders DOM for free-text natively
    if not JINA_API_KEY:
        print("🔵 DEEP CRAWL SKIPPED: Missing JINA_API_KEY. Falling back to Dual-Drone.")
        return layer2_perplexity(restaurant_name, location)

    print(f"🟣 DEEP CRAWL ACTIVE: Jina DOM-Rendering Drone for {restaurant_name} {location}...")
    try:
        headers = {
            "Authorization": f"Bearer {JINA_API_KEY}",
            "X-Target-Selector": "body"
        }
        query = f"{restaurant_name} official allergen menu ingredients"
        response = requests.get(f"https://s.jina.ai/{query}", headers=headers, timeout=20)
        
        data = response.text
        if len(data) < 500:
            print("🟡 DEEP CRAWL FAILED: Could not scrape DOM. Falling back to Dual-Drone.")
            return layer2_perplexity(restaurant_name, location)
            
        return f"DEEP CRAWL JINA DATA:\n{data[:8000]}" # Cap to 8000 to avoid token blowouts
    except Exception as e:
        print(f"❌ DEEP CRAWL ERROR: {e}. Falling back to Dual-Drone.")
        return layer2_perplexity(restaurant_name, location)


def layer2b_migraine_sentiment(restaurant_name: str, location: str) -> str:
    """LAYER 2B: The Migraine Drone. Dedicated scraping for social sentiment on Yelp/Reddit."""
    if not OPENROUTER_API_KEY:
        return "SOCIAL SENTIMENT: Migraine Drone Offline (No API Key)"
        
    print(f"🟣 LAYER 2B ACTIVE: Deploying Migraine Sentiment Drone for {restaurant_name}...")
    try:
        response = openrouter_client.chat.completions.create(
            model="perplexity/sonar",
            messages=[
                {"role": "system", "content": "You are a specialized medical sentiment drone scanning Reddit, Yelp, and TikTok reviews. You must find out what exact menu items from the restaurant are most strongly accused of causing 'migraines' or 'headaches' due to additives or MSG. You MUST output EXACT dish names (e.g., 'Orange Chicken', 'Beef and Cheddar'). If no specific dishes are explicitly named, but people generally complain about migraines there, extrapolate the top 2 signature dishes most likely responsible and output them. If absolutely zero migraine complaints exist anywhere, respond exactly: NO_MIGRAINE_REPORTS_FOUND."},
                {"role": "user", "content": f"Search user reviews for {restaurant_name} near {location} for headache or migraine triggers. What exact dishes are causing them?"}
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


def layer3_gpt4o_compile(restaurant_name: str, context: str, profiles: list, used_source: str, social_sentiment: str = "", excluded_dishes: list = []) -> dict:
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
    1. STRICT INGREDIENT REPORTING: You must provide a simple, flat array of atomic ingredient names for each dish. Each ingredient must be a SHORT, PLAIN ingredient name (e.g. 'Soy Sauce', 'Cornstarch', 'Natural Flavors'). NEVER write nested parenthetical sub-formulas. Each array item must be a single, atomic ingredient string. NO nesting. MINIMUM 6 ingredients per dish — a dish with 2 ingredients like 'Ground Beef, Taco Shell' is WRONG and incomplete.
    2. THE "COMMERCIAL BASELINE" SYNTHESIS — CRITICAL DEPTH RULE: You are an industrial food scientist with access to commercial supply-chain knowledge. For every dish, you MUST penetrate the ingredient label down to the actual chemical supply-chain level. Examples:
       - "Taco Bell Seasoned Beef" → MUST list its components: Ground Beef, Yeast Extract, Natural Flavors, Maltodextrin, Spices, Salt, Chili Pepper, Paprika
       - "KFC Grilled Chicken" → MUST include: Monosodium Glutamate, Salt, Spices in the seasoning blend
       - "Generic Teriyaki Sauce" → MUST list: Soy Sauce, Sugar, Water, Cornstarch, Natural Flavors (NOTE: Here, 'Natural Flavors' triggers UNCERTAIN. Do not inject 'Yeast Extract' unless it is a definitive industry standard for that chain.)
       - "House Vinaigrette" → MUST list: Vegetable Oil, Vinegar, Spices, Natural Flavors
       If a dish has pre-made sauces, seasonings, or marinades, you MUST enumerate the chemical ingredients of those sub-components. MUST NOT auto-inject "Yeast Extract" or "MSG" into every single sauce unless it is a guaranteed industry standard for that chain. Allow "Natural Flavors" and "Soy Sauce" to stand alone for ambiguous items, which correctly triggers UNCERTAIN.
    3. ASSIGN THE SOURCE ENUM: Set 'ingredient_source' exactly matching the provided DATA ACQUISITION SOURCE: "{used_source}".
    4. NO VAGUE HEDGING: The UI renders the 'ingredients' array as chemical chips. Be precise and flat.
    5. USER-FRIENDLY INFERENCE (NO 'TIER' JARGON): Explain the risk of the 'ingredients' array in plain, simple English. DO NOT use the word 'Tier' or 'Tier 1/2/3'. Instead, say exactly why it's harmful, e.g. "Natural Flavors is a high-risk hidden additive," or "Yeast Extract is a guaranteed MSG carrier." If it is safe, say "Contains no MSG-related ingredients."
    6. STRICT FIDELITY + DENSITY: 
       - If SOURCE is 'SPOONACULAR_DB': You MUST analyze and synthesize ingredients for EVERY SINGLE DISH provided in the background context. DO NOT SKIP ANY DISH. If there are 35 dishes listed, you MUST output an array of 35 items. Skipping dishes is a critical system failure.
       - If SOURCE is 'PERPLEXITY_LIVE_SCRAPE': ONLY output the exact dishes with ingredients found in BACKGROUND CONTEXT verbatim. Output EVERY SINGLE ONE.
       - If SOURCE is 'COMMERCIAL_SYNTHESIS': You MUST generate exactly 30 to 35 most famous real menu items for that exact restaurant. Outputting fewer than 25 items is a critical systemic failure. INCLUDE a diverse mix of entrees AND the plain unprocessed sides.
    7. STRICT FILTERING: Drop all soft drinks, sodas, and generic beverages. Furthermore, DROP all individual raw ingredients, fragmented components, and solo condiments (e.g., 'Lettuce', 'Mustard', 'Sauce', 'Pattie'). ONLY output true full food dishes: completely assembled entrees, appetizers, desserts, and side-dishes.
    7b. SAUCE SAFETY PANEL (SEPARATE ARRAY): Separately, you MUST populate the top-level `sauces` array with ALL dipping sauces, condiments, and dressings available at this restaurant (e.g. Ketchup, Ranch, BBQ Sauce, Honey Mustard, Secret Sauce, Buffalo Sauce, Sriracha). For each sauce, classify it as SAFE, UNCERTAIN, or UNSAFE using the exact same MSG Chemical Database rules. Provide a one-sentence reason. Aim for 6–12 sauces. This array is COMPLETELY SEPARATE from the main `results` dish array.
    8. EVIDENCE-BASED CLASSIFICATION — THIS IS THE ONLY RULE THAT DETERMINES STATUS:
       - SAFE: Assign ONLY when the ingredients array is 100% clean (no MSG definitions). Simple, unprocessed items MUST be SAFE with HIGH confidence.
       - UNCERTAIN: Assign when there is a 'High-Risk Additive / Loophole' (e.g., Natural Flavors, Bouillon, Soy Sauce) OR an ambiguous sauce/marinade present. These are "possibly safe" but require server verification.
       - UNSAFE: Assign ONLY when the dish contains 'DIRECT MSG / GUARANTEED CARRIERS' (e.g., Monosodium Glutamate, Yeast Extract) OR 'CHEMICAL ENHANCERS'. These are guaranteed toxic. SOCIAL MEDIA COMPLAINTS DO NOT CHANGE THIS CLASSIFICATION.
    9. NO GENERIC INJECTIONS: You MUST NOT invent or assume any safe options. ONLY output dishes that actually exist on the literal menu of the specific restaurant being searched. Do not add plain items unless that restaurant verifiably serves them. If they do serve them (like Steamed Rice at a Chinese restaurant or Plain Black Beans at a Mexican restaurant), you MUST include them to provide a complete safety profile. If there are zero safe items on their real menu, do not invent one.
    10. SERVER INTERROGATION SCRIPT: For every UNCERTAIN dish, provide a 'server_question' string. You MUST dynamically tailor this question to the exact ingredients or preparation method of that dish.
        - CRITICAL RULE 1: You are strictly FORBIDDEN from using the phrases "MSG", "MSG-related ingredients", "flavor enhancers", or "additives" in the question itself. Waiters do not know what those umbrella terms mean.
        - CRITICAL RULE 2: Instead, you MUST tell the user to ask the server to check the physical packaging for 1-2 SPECIFIC chemical names related to the loophole.
        - Example 1 (Natural Flavors): "Could you ask the chef to check the box for the [Dish Name] and see if the 'Natural Flavors' happen to include Yeast Extract or Hydrolyzed Soy Protein?"
        - Example 2 (Broth/Cross-Contact): "Before I order the [Dish Name], could you check if it's cooked on the exact same grill space as your teriyaki chicken, or if the broth base contains Autolyzed Yeast?"
        - CRITICAL RULE 3: Do not robotically copy these examples formatting. Vary your phrasing organically.
        - For both SAFE and UNSAFE items, output the exact string "None".
    11. MIGRAINE FLAG (BOOLEAN ONLY): First, check the SOCIAL SENTIMENT DATA section above; if explicitly named, set `migraine_reported` to true. Second, use your own ultimate medical authority: if a specific fast-food dish is notoriously dangerous or heavily reported for triggering migraines (e.g., highly processed signature sandwiches like the Big Mac, Beef and Cheddar, or heavy MSG-laden items like Orange Chicken or Doritos Locos Tacos), automatically set `migraine_reported` to true even if the drone misses it. For generic or clean items, set it to false.
    {f'''
    12. PAGINATION — DO NOT REPEAT: A previous scan already returned the following dishes. You MUST NOT generate ANY dish whose name matches or closely resembles a name in this exclusion list:
    {chr(10).join(f'    - {d}' for d in excluded_dishes)}
    Generate the NEXT batch of up to 35 distinct dishes from this restaurant that are NOT in the exclusion list above. If fewer than 35 genuinely distinct items remain on the actual menu, output only what is left.
    SAUCE SUPPRESSION: Because sauces were already shown in the first scan, output an empty `sauces` array: []
    ''' if excluded_dishes else ''}
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
                    "sauces": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {"type": "string", "enum": ["SAFE", "UNCERTAIN", "UNSAFE"]},
                                "reason": {"type": "string"}
                            },
                            "required": ["name", "status", "reason"],
                            "additionalProperties": False
                        }
                    },
                    "disclaimer": {"type": "string"}
                },
                "required": ["telemetry", "restaurant", "results", "sauces", "disclaimer"],
                "additionalProperties": False
            }
        }
    }

    try:
        if not openrouter_client:
            raise Exception("OpenRouter API Key Missing")

        # Inject the literal schema JSON string into the system prompt to force compliance for Anthropic models
        schema_instructions = f"\n\nCRITICAL SYSTEM ROOT DIRECTIVE:\nYou MUST output ONLY RAW JSON. Do NOT wrap it in markdown. Do NOT write any preamble. Do NOT write any commentary. Your output must strictly adhere to the following JSON schema:\n{json.dumps(final_output_schema)}"
        
        response = openrouter_client.chat.completions.create(
            model="anthropic/claude-3.7-sonnet",
            temperature=0.1,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": system_prompt + schema_instructions},
                {"role": "user", "content": f"Compile the final STRICT json payload for {restaurant_name} using the context provided. CRITICAL: If Data Source is COMMERCIAL_SYNTHESIS, you MUST generate at least 30 item objects in your results array. Do not be lazy. If Data Source is SPOONACULAR/PERPLEXITY, extract every single dish provided without skipping any. Generating fewer than 25 results is a systemic failure."}
            ] # We explicitly omit 'response_format' as OpenRouter hangs on strict json schemas for Anthropic
        )
        
        raw_output = response.choices[0].message.content
        # Strip potential markdown wrappers that Anthropic occasionally includes
        clean_json = raw_output.replace('```json', '').replace('```', '').strip()
        
        return json.loads(clean_json)
    except Exception as e:
        print(f"❌ Layer 3 Brain Failure: {e}")
        return {}


def analyze_allergens(restaurant_name: str, location: str, profiles: list, excluded_dishes: list = [], deep_scan: bool = False) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    
    source_tag = "UNCERTAIN"
    context = ""
    social_context = ""
    
    # Launch social sentiment drone immediately in the background
    # It runs while Layers 1 and 2 do their sequential work
    executor = ThreadPoolExecutor(max_workers=1)
    future_social = executor.submit(layer2b_migraine_sentiment, restaurant_name, location)
    
    # Layer 2: Perplexity Dual Drone OR Deep Crawl
    if deep_scan:
        context = layer2_deep_crawl(restaurant_name, location)
        source_tag = "DEEP_CRAWL_DOM_RENDER" if "DEEP CRAWL JINA DATA" in context else "PERPLEXITY_DUAL_DRONE"
    else:
        context = layer2_perplexity(restaurant_name, location)
        if context:
            source_tag = "PERPLEXITY_DUAL_DRONE"
    
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
        social_sentiment=social_context,
        excluded_dishes=excluded_dishes
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
