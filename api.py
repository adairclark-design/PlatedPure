from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import asyncio
import sys
import os
import json as json_mod

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
    excluded_dishes: List[str] = []  # Dish names already shown — used for "Continue the Search" pagination
    deep_scan: bool = False  # Triggers the heavy Firecrawl Javascript DOM rendering pipeline

@app.get("/ping")
async def ping():
    """Lightweight health check used by the frontend to pre-warm the server on page load."""
    return {"status": "awake"}

@app.post("/analyze")
async def analyze_restaurant(request: AnalyzeRequest):
    """
    Takes a single restaurant name/location and a list of human dietary profiles.
    Instructs the AI to search the web and deduce safe/unsafe menu matches.
    """
    try:
        print(f"📡 API HIT: Analyzing '{request.restaurant_name}' for {len(request.profiles)} profiles. Excluded dishes: {len(request.excluded_dishes)} | Deep Scan: {request.deep_scan}")
        
        # Convert Pydantic objects to standard dictionaries for the backend tool
        profiles_list = [p.model_dump() for p in request.profiles]
        
        # Execute Layer 3 Tool
        result = analyze_allergens(
            restaurant_name=request.restaurant_name,
            location=request.location,
            profiles=profiles_list,
            excluded_dishes=request.excluded_dishes,
            deep_scan=request.deep_scan
        )
        
        return result
    
    except Exception as e:
        print(f"❌ API ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="The AI Analyzer encountered an unexpected error.")

@app.post("/analyze-stream")
async def analyze_restaurant_stream(request: AnalyzeRequest):
    """
    SSE streaming version of /analyze. Emits live status events during
    each pipeline phase so the frontend can show real-time progress.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def status_callback(phase: str, message: str):
        """Called from the sync worker thread — pushes status into the async queue."""
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "status", "phase": phase, "message": message})

    async def event_generator():
        profiles_list = [p.model_dump() for p in request.profiles]

        async def run_analysis():
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: analyze_allergens(
                        restaurant_name=request.restaurant_name,
                        location=request.location,
                        profiles=profiles_list,
                        excluded_dishes=request.excluded_dishes,
                        deep_scan=request.deep_scan,
                        status_callback=status_callback,
                    )
                )
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "result", "data": result})
            except Exception as e:
                print(f"❌ STREAM ERROR: {e}")
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        asyncio.create_task(run_analysis())

        while True:
            item = await queue.get()
            if item is None:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json_mod.dumps(item)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

if __name__ == "__main__":
    # Boot up the Uvicorn server automatically if run via `python api.py`
    print("🚀 Booting up PlatedPure FastAPI Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
