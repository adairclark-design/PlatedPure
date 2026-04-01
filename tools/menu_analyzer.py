import os
import sys
import json
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = OpenAI()

def search_web(query: str, max_results: int = 5) -> str:
    """Tool: Searches the web and returns titles, text, and URLs."""
    print(f"🤖 Agent Action: Searching web for '{query}'")
    try:
        results = list(DDGS().text(query, max_results=max_results))
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {e}"})

def read_url(url: str) -> str:
    """Tool: Downloads and extracts text from a given URL, including PDFs."""
    print(f"🤖 Agent Action: Reading URL '{url}'")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=8)
        
        if resp.status_code != 200:
            return json.dumps({"error": f"HTTP {resp.status_code}"})
            
        # PDF parsing
        if 'pdf' in resp.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf'):
            try:
                doc = fitz.open(stream=resp.content, filetype='pdf')
                # Read first 12 pages only to prevent token explosion
                text = "\n".join([doc[i].get_text() for i in range(min(12, len(doc)))])
                return json.dumps({"type": "pdf", "text": text[:15000]})
            except Exception as pdf_e:
                return json.dumps({"error": f"PDF parse failed: {pdf_e}"})
                
        # HTML text parsing
        soup = BeautifulSoup(resp.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return json.dumps({"type": "html", "text": " ".join(text.split())[:10000]})
        
    except requests.Timeout:
        return json.dumps({"error": "Request timed out"})
    except Exception as e:
        return json.dumps({"error": f"Read failed: {e}"})

def analyze_allergens(restaurant_name: str, location: str, profiles: list) -> dict:
    """
    Agentic Web Researcher Engine. Actively uses tools to hunt down exact PDF/HTML ingredient lists.
    """
    system_prompt = """
    You are an elite, autonomous Agentic Web Crawler designed to protect patients with severe Monosodium Glutamate intolerances.
    
    You have access to two tools: `search_web` and `read_url`. 
    
    YOUR MISSION: 
    1. DO NOT GUESS INGREDIENTS. 
    2. You must actively search for the OFFICIAL ingredient list for the target restaurant/brand (e.g. search for "restaurant name official ingredients PDF" or "restaurant name allergen nutrition guide").
    3. If you find a promising URL (like a PDF or an official site), you MUST use `read_url` to download its text.
    4. Keep iterating (searching and reading) until you find the exact ingredients for their menu, or until you are absolutely certain the data is not publicly available.

    THE ABSOLUTE MSG CHEMICAL DATABASE (Identify all loopholes):
    - [TIER 1] GUARANTEED MSG: Monosodium Glutamate (E621), Yeast Extract, Autolyzed Yeast, Hydrolyzed Veg/Soy Protein, Calcium Caseinate, Torula Yeast.
    - [TIER 2] HIGH PROBABILITY: Natural Flavors, Artificial Flavors, Bouillon, Broth, Maltodextrin, Pectin, Soy Sauce.
    - [TIER 3] ENHANCERS: Disodium 5'-guanylate, Disodium 5'-inosinate.
    
    CRITICAL BEHAVIORAL RULES:
    1. STRICT EVIDENCE REPORTING: For every single dish, separate your analysis into 'verified_ingredients' and 'culinary_inference'.
    2. VERIFIED INGREDIENTS: If and ONLY IF you retrieved an exact, verifiable list of ingredients using your tools, put them as an array of strings in 'verified_ingredients'. If exact data was hidden or not found, this array MUST be empty []. DO NOT hallucinate.
    3. CULINARY INFERENCE: Explain the risk. If you have verified ingredients, explain exactly which ones match the MSG Danger Tiers. If 'verified_ingredients' is empty, explicitly state "Official exact ingredients unavailable." and then explain standard culinary preparation risks.
    4. You MUST output a minimum of 15-20 realistic menu items for restaurants (including safe baseline items like plain white rice), and 4-5 items for grocery brands.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Searches the internet and returns titles, URL links, and text snippets. Use this to find official ingredient PDFs or nutrition pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query (e.g. 'Panda Express official ingredients filetype:pdf')"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_url",
                "description": "Downloads the full text content from a specific URL. Supports both HTML websites and direct PDF links.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The full HTTPS URL to read"}
                    },
                    "required": ["url"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Execute an aggressive search for exact ingredient data for: {restaurant_name} (Location context: {location}). Once you have sufficient unstructured data from your tools, compile your final JSON payload matching the OUTPUT SCHEMA documented previously."}
    ]

    
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
                                "verified_ingredients": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "culinary_inference": {"type": "string"},
                                "confidence": {"type": "string", "enum": ["HIGH", "LOW"]}
                            },
                            "required": ["dish_name", "status", "flagged_by", "verified_ingredients", "culinary_inference", "confidence"],
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

    print("🚀 Initiating Autonomous PDF & Web Crawler Agent...")
    urls_crawled = 0
    chars_scraped = 0
    
    # We allow the agent up to 6 iterations to use tools before forcing an answer.
    for i in range(6):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.1,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            # If the model didn't call a tool, it generated its final text response based on its instructions, but we need it in JSON.
            # We'll handle forcing JSON format if it finishes early. Actually, we should just let it output the final response format if we set response_format.
            # But OpenAI prevents combining tool_choice auto with json_schema in some cases. It's safer to separate the loop and the final compilation.
            pass
            
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")
            sys.exit(1)

        # Append assistant's message (which contains tool calls or text)
        messages.append(message)
        
        if not getattr(message, "tool_calls", None):
            # No tool calls means the agent has decided it's done gathering information.
            break

        # Execute tool calls
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if function_name == "search_web":
                tool_result = search_web(query=args.get("query"))
                chars_scraped += len(tool_result)
            elif function_name == "read_url":
                tool_result = read_url(url=args.get("url"))
                chars_scraped += len(tool_result)
                urls_crawled += 1
            else:
                tool_result = json.dumps({"error": "Unknown tool"})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    # FINAL COMPILATION PHASE: Agent has gathered data, now force it to output JSON matching the strict schema.
    print("🧠 Forcing Agent to compile findings into Strict Schema...")
    messages.append({
        "role": "user", 
        "content" : "Data gathering phase complete. Generate the final exact JSON payload conforming STRICTLY to the MSG schema. Include ALL verified ingredients you discovered. Do not call any more tools."
    })
    
    try:
        final_response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            messages=messages,
            response_format=final_output_schema
        )
        payload = json.loads(final_response.choices[0].message.content)
        
        # Override telemetry with actual loop variables
        payload['telemetry']['chars_scraped'] = chars_scraped
        payload['telemetry']['urls_crawled'] = urls_crawled
        return payload
    except Exception as e:
        print(f"❌ Final JSON Parsing Error: {e}")
        return {}


if __name__ == "__main__":
    test_profiles = [
        {"name": "MSG Scanner", "restrictions": ["MSG-Free"]}
    ]
    print("Starting Headless PDF Agent...")
    final_payload = analyze_allergens("McDonalds", "Oregon", test_profiles)
    print("\n📦 FINAL OUTCOME:\n", json.dumps(final_payload, indent=2))
