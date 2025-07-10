import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import database
import uuid
import os
import google.generativeai as genai

gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# Pydantic Models
class HealthData(BaseModel):
    heightFeet: int
    heightInches: int
    weight: int
    activityLevel: str

class MealPlan(BaseModel):
    meal_plan: List[Dict[str, Any]]
    class Config:
        extra = "allow"

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_meal_plan_from_gemini(health_data: HealthData):
    prompt = f"""
    Based on the following health profile for a person in the USA, create a personalized 7-day meal plan:
    - Height: {health_data.heightFeet} feet, {health_data.heightInches} inches
    - Weight: {health_data.weight} lbs
    - Activity Level: {health_data.activityLevel.replace('_', ' ')}
    Your task is to generate a simple, healthy, and balanced meal plan with common American foods and standard portion sizes.
    Please provide the output in a structured JSON format. The root object should be a single JSON object.
    The JSON object should have a single key 'meal_plan' which is an array of 7 day objects.
    Each day object should have the following keys: 'day', 'breakfast', 'lunch', 'dinner', and 'snacks'.
    The value for breakfast, lunch, dinner, and snacks should be a string describing the meal.
    Ensure the entire output is a single, valid JSON object. Do not include any text or markdown formatting. The response string should be a valid JSON response, and nothing else. Make sure it is valid JSON.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        content = response.text.strip()
        content = content.replace('```json', '').replace('```', '').strip()
        return content
    except Exception as e:
        print(f"Gemini meal plan error: {e}")
        return None


def extract_grocery_list_from_gemini(meal_plan_text: str):
    prompt = f"""
    Analyze the following 7-day meal plan and extract a consolidated grocery list.\n\nMeal Plan:\n{meal_plan_text}\n\nYour task is to:\n1. Identify all unique ingredients required for the entire week.\n2. Consolidate the quantities. Use standard US grocery units (e.g., lbs, oz, cups, or by item count like '2 apples').\n3. Categorize the items (e.g., 'Produce', 'Protein', 'Dairy & Alternatives', 'Pantry').\n4. For each item, search the web and provide a real, working product link from the Tesco Ireland grocery store (https://www.tesco.com/groceries/). Do not use placeholder links or any other store.\n5. For each item, extract its protein, carbs, fats, and calories.\n6. Provide the output as a single, valid JSON object. The root object should have a single key 'grocery_list' which is an array of item objects.\n7. Each item object must have the following keys: 'item', 'quantity', 'category', 'link', 'protein', 'carbs', 'fats', and 'cals'.\n\nExample format:\n{{\n  \"grocery_list\": [\n    {{\n      \"item\": \"Chicken Breast\",\n      \"quantity\": \"2 lbs\",\n      \"category\": \"Protein\",\n      \"link\": \"https://www.tesco.com/groceries/en-GB/products/123456789\",\n      \"protein\": \"50g\",\n      \"carbs\": \"0g\",\n      \"fats\": \"5g\",\n      \"cals\": \"250\"\n    }}\n  ]\n}}\n\nEnsure the entire output is a single, valid JSON object without any surrounding text or markdown.\n    """
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        content = response.text.strip()
        content = content.replace('```json', '').replace('```', '').strip()
        return content
    except Exception as e:
        print(f"Gemini grocery list error: {e}")
        return None

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/mealplan")
def generate_meal_plan_endpoint(health_data: HealthData):
    print("Received health data:", health_data)
    try:
        raw_meal_plan = generate_meal_plan_from_gemini(health_data)
        print("Raw meal plan from Gemini:", raw_meal_plan)
        if not raw_meal_plan:
            print("Meal plan generation failed (None returned)")
            raise HTTPException(status_code=500, detail="Failed to generate meal plan from AI.")
        print("Attempting to parse meal plan as JSON string.")
        try:
            meal_plan_json = json.loads(raw_meal_plan)
            print("Parsed meal plan JSON:", meal_plan_json)
            return meal_plan_json
        except Exception as e:
            print(f"JSON decode error: {e}")
            return {"raw": raw_meal_plan, "error": str(e)}
    except Exception as e:
        import traceback
        print("Unexpected error in /mealplan endpoint:", traceback.format_exc())
        return {"error": str(e)}

@app.post("/grocery-list")
def create_grocery_list_endpoint(meal_plan: MealPlan):
    try:
        meal_plan_text = json.dumps(meal_plan.dict())
        raw_grocery_list = extract_grocery_list_from_gemini(meal_plan_text)
        if not raw_grocery_list:
            raise HTTPException(status_code=500, detail="Failed to extract grocery list from AI.")
        try:
            grocery_list_json = json.loads(raw_grocery_list)
            return grocery_list_json
        except Exception as e:
            print(f"JSON decode error: {e}")
            return {"raw": raw_grocery_list, "error": str(e)}
    except Exception as e:
        print(f"Unexpected error in /grocery-list endpoint: {str(e)}")
        return {"error": str(e)}

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

# Utility: List available Gemini models for debugging
@app.get("/gemini-models")
def list_gemini_models():
    try:
        models = genai.list_models()
        model_names = [m.name for m in models]
        return {"models": model_names}
    except Exception as e:
        return {"error": str(e)}
