import sys
from duckduckgo_search import DDGS

def test_free_restaurant_scrape(restaurant_name: str, location: str):
    """
    Simulates finding restaurant menu data entirely for free without the $229 Yelp API.
    """
    print(f"🔍 Searching DDG for menu data about: {restaurant_name} in {location}...\n")
    search_query = f"{restaurant_name} {location} menu reviews"
    
    try:
        results = DDGS().text(search_query, max_results=3)
        
        print("✅ SUCCESS: Snagged raw web context without any API keys or Cloudflare blocks:\n")
        
        for idx, result in enumerate(results, 1):
            print(f"--- Result {idx} ---")
            print(f"Title: {result.get('title')}")
            print(f"Snippet: {result.get('body')}")
            print(f"Link: {result.get('href')}\n")
            
        print("🤖 Next Step: Feed these dense snippets directly to OpenAI GPT-4o for allergen reasoning.")
        
    except Exception as e:
        print(f"❌ ERROR: Search failed. Details: {str(e)}")
        print("Note: You may need to run `pip install duckduckgo-search` first.")

if __name__ == "__main__":
    test_free_restaurant_scrape("Bottega", "Yountville, CA")
