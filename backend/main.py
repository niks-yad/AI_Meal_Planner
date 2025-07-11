import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import database
import uuid
import httpx # Added: Import httpx for making HTTP requests
# Import the mcp_app from the new mcp_server.py
from mcp_server import mcp_app # Modified: Import mcp_app instead of mcp and tools

# Pydantic Models
class HealthData(BaseModel):
    heightFeet: int
    heightInches: int
    weight: int
    activityLevel: str

class MealPlan(BaseModel):
    meal_plan: List[Dict[str, Any]]
    # class Config:
    #     extra = "allow"

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP application
app.mount("/mcp", mcp_app) # Added: Mount the FastMCP HTTP application

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/mealplan")
async def generate_meal_plan_endpoint(health_data: HealthData):
    print("Received health data:", health_data)
    try:
        # Make an HTTP request to the MCP tool endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post("http://127.0.0.1:8000/mcp/tools/generate_meal_plan", json=health_data.dict())
            response.raise_for_status() # Raise an exception for bad status codes
            meal_plan_result = response.json()
        
        print("Meal plan result from MCP tool:", meal_plan_result)

        if "error" in meal_plan_result:
            raise HTTPException(status_code=500, detail=meal_plan_result["error"])

        return meal_plan_result
    
    except httpx.HTTPStatusError as e:
        print(f"HTTP error in /mealplan endpoint: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to generate meal plan from MCP: {e.response.text}")
    
    except Exception as e:
        import traceback
        print("Unexpected error in /mealplan endpoint:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate meal plan: {e}")

@app.post("/grocery-list")
async def create_grocery_list_endpoint(meal_plan: MealPlan):
    try:
        # Make an HTTP request to the MCP tool endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post("http://127.0.0.1:8000/mcp/tools/extract_grocery_list", json=meal_plan.dict())
            response.raise_for_status() # Raise an exception for bad status codes
            grocery_list_result = response.json()

        print("Grocery list result from MCP tool:", grocery_list_result)

        if "error" in grocery_list_result:
            raise HTTPException(status_code=500, detail=grocery_list_result["error"])

        # Generate a session ID and store the grocery list in the database
        session_id = str(uuid.uuid4())
        database.insert_grocery_list(session_id, grocery_list_result)

        return {"session_id": session_id, "grocery_list": grocery_list_result}
    except httpx.HTTPStatusError as e:
        print(f"HTTP error in /grocery-list endpoint: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to create grocery list from MCP: {e.response.text}")
    except Exception as e:
        import traceback
        print(f"Unexpected error in /grocery-list endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create grocery list: {e}")

@app.get("/grocery-list/{session_id}")
def get_grocery_list_endpoint(session_id: str):
    grocery_list = database.get_grocery_list(session_id)
    if not grocery_list:
        raise HTTPException(status_code=404, detail="Grocery list not found.")
    return {"grocery_list": grocery_list}

@app.delete("/grocery-list/{session_id}")
def delete_grocery_list_endpoint(session_id: str):
    database.delete_grocery_list(session_id)
    return {"message": f"Grocery list for session {session_id} deleted."}
