from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import sys
import os

# Ensure the tools directory is accessible for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.menu_analyzer import analyze_allergens

app = FastAPI(title="Additive Detective Server", version="1.0.0")

# Enable CORS so the React/Vite local dev server can communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing. Update for prod Cloudflare URL later.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic models mapping to our gemini.md Data Schema
class Profile(BaseModel):
    name: str
    restrictions: List[str]

class AnalyzeRequest(BaseModel):
    restaurant_name: str
    location: str
    profiles: List[Profile]

@app.post("/analyze")
async def analyze_restaurant(request: AnalyzeRequest):
    """
    Takes a single restaurant name/location and a list of human dietary profiles.
    Instructs the AI to search the web and deduce safe/unsafe menu matches.
    """
    try:
        print(f"📡 API HIT: Analyzing '{request.restaurant_name}' for {len(request.profiles)} profiles.")
        
        # Convert Pydantic objects to standard dictionaries for the backend tool
        profiles_list = [p.model_dump() for p in request.profiles]
        
        # Execute Layer 3 Tool
        result = analyze_allergens(
            restaurant_name=request.restaurant_name,
            location=request.location,
            profiles=profiles_list
        )
        
        return result
    
    except Exception as e:
        print(f"❌ API ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="The AI Analyzer encountered an unexpected error.")

if __name__ == "__main__":
    # Boot up the Uvicorn server automatically if run via `python api.py`
    print("🚀 Booting up PlatedPure FastAPI Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
