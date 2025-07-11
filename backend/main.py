import json
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import database
import uuid

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def _get_gemini_model():
    """Initializes and returns the Gemini model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

# FastMCP instance - will be used to generate MCP server from FastAPI app
mcp = FastMCP("walmart-meal-planner")

@app.post("/mcp/tools/generate_meal_plan", operation_id="generate_meal_plan")
async def generate_meal_plan_tool(
    heightFeet: int,
    heightInches: int,
    weight: int,
    activityLevel: str,
    days: int = 7
) -> dict:
    """Generate a personalized meal plan based on user preferences and health data."""
    logger.info(f"MCP Tool: generate_meal_plan called with: heightFeet={heightFeet}, heightInches={heightInches}, weight={weight}, activityLevel={activityLevel}")
    model = _get_gemini_model()
    prompt = f"""
    Based on the following health profile for a person in the USA, create a personalized {days}-day meal plan:
    - Height: {heightFeet} feet, {heightInches} inches
    - Weight: {weight} lbs
    - Activity Level: {activityLevel.replace('_', ' ')}
    Your task is to generate a simple, healthy, and balanced meal plan with common American foods and standard portion sizes.
    Make sure to reuse groceries whever possible as we want to minimize waste and cost. Some foods expire withint days, so less is more but dont compromise on quality.
    The JSON object should have a single key "meal_plan" which is an array of {days} day objects.
    Each day object should have the following keys: "day", "breakfast", "lunch", "dinner", and "snacks".
    The value for breakfast, lunch, dinner, and snacks should be a string describing the meal.
    Ensure the entire output is a single, valid JSON object. Do not include any text or markdown formatting. The response string should be a valid JSON response, and nothing else. Make sure it is valid JSON.
    """
    try:
        logger.info("Sending prompt to Gemini for meal plan generation via MCP tool.")
        response = model.generate_content(prompt)
        logger.info(f"Raw Gemini response: {response.text}")
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        logger.info(f"Cleaned Gemini response: {cleaned_response}")
        try:
            meal_plan_json = json.loads(cleaned_response)
            logger.info("Successfully parsed meal plan JSON on first attempt.")
        except json.JSONDecodeError as e:
            logger.error(f"Initial meal plan JSON parsing failed: {e}. Attempting correction with Gemini.")
            correction_prompt = f"""
            The following text was intended to be a JSON object, but it failed to parse.\nPlease correct it to be a valid JSON object, ensuring it strictly follows the specified format for a meal_plan.\nDo not include any conversational text, markdown formatting (like ```json), or extra characters outside the JSON object.\n\nOriginal problematic text:\n{cleaned_response}\n\nExpected JSON format (root object with 'meal_plan' key, which is an array of {days} day objects):\n{{\n  "meal_plan": [\n    {{\n      "day": "Monday",\n      "breakfast": "...",\n      "lunch": "...",\n      "dinner": "...",\n      "snacks": "..."\n    }}\n  ]\n}}\n"""
            correction_response = model.generate_content(correction_prompt)
            logger.info(f"Gemini correction response: {correction_response.text}")
            corrected_response_text = correction_response.text.strip()
            json_start = corrected_response_text.find('{')
            json_end = corrected_response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                final_cleaned_response = corrected_response_text[json_start : json_end + 1]
                logger.info(f"Final cleaned corrected response: {final_cleaned_response}")
            else:
                logger.error("Corrected AI response still does not contain a valid JSON object.")
                raise ValueError("Corrected AI response still does not contain a valid JSON object.")
            meal_plan_json = json.loads(final_cleaned_response)
        return meal_plan_json
    except Exception as e:
        logger.error(f"Error generating meal plan with Gemini via MCP tool: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/tools/extract_grocery_list", operation_id="extract_grocery_list")
async def extract_grocery_list_tool(meal_plan: dict) -> list:
    """Extract grocery items from a meal plan."""
    logger.info("MCP Tool: extract_grocery_list called.")
    model = _get_gemini_model()
    meal_plan_text = json.dumps(meal_plan)
    prompt = f"""
    Analyze the following 7-day meal plan and extract a consolidated grocery list.\n\nMeal Plan:\n{meal_plan_text}\n\nYour task is to:\n1. Identify all unique ingredients required for the entire week.\n2. Consolidate the quantities. Use standard US grocery units (e.g., lbs, oz, cups, or by item count like "2 apples").\n3. Categorize the items (e.g., "Produce", "Protein", "Dairy & Alternatives", "Pantry").\n4. For each item, search for it on "Tesco Ireland" and find a working product link on tesco.ie/groceries/product/.\n5. For each item, extract its protein, carbs, fats, and calories.\n6. Provide the output as a single, valid JSON object. The root object should have a single key "grocery_list" which is an array of item objects.\n7. Each item object must have the following keys: "item" (the name of the ingredient), "quantity" (a string with the amount and unit), "category", "link" (the Tesco product link, or null if not found), "protein" (in grams), "carbs" (in grams), "fats" (in grams), and "cals" (calories).\n\nExample format:\n{{
  "grocery_list": [
    {{
      "item": "Chicken Breast",
      "quantity": "2 lbs",
      "category": "Protein",
      "link": "https://www.tesco.ie/groceries/product/details/some-chicken-link",
      "protein": "50g",
      "carbs": "0g",
      "fats": "5g",
      "cals": "250"
    }},
    {{
      "item": "Apple",
      "quantity": "3",
      "category": "Produce",
      "link": "https://www.tesco.ie/groceries/product/details/some-apple-link",
      "protein": "0.5g",
      "carbs": "14g",
      "fats": "0.3g",
      "cals": "52"
    }}\n  ]\n}}\n\nEnsure the entire output is a single, valid JSON object without any surrounding text or markdown.\n    """
    try:
        logger.info("Sending prompt to Gemini for grocery list extraction via MCP tool.")
        response = model.generate_content(prompt)
        logger.info(f"Raw Gemini response: {response.text}")
        response_text = response.text.strip()

        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                cleaned_response = response_text[json_start : json_end + 1]
                logger.info(f"Cleaned Gemini grocery response: {cleaned_response}")
            else:
                logger.error("No valid JSON object found in AI response.")
                raise ValueError("No valid JSON object found in AI response.")
            grocery_list_json = json.loads(cleaned_response)
            logger.info("Successfully parsed grocery list JSON on first attempt.")
        except json.JSONDecodeError as e:
            logger.error(f"Initial JSON parsing failed: {e}. Attempting correction with Gemini.")
            correction_prompt = f"""
            The following text was intended to be a JSON object, but it failed to parse.\n            Please correct it to be a valid JSON object, ensuring it strictly follows the specified format for a grocery_list.\n            Do not include any conversational text, markdown formatting (like ```json), or extra characters outside the JSON object.\n\n            Original problematic text:\n            {response_text}\n\n            Expected JSON format (root object with "grocery_list" key, which is an array of item objects):\n            {{
              "grocery_list": [
                {{
                  "item": "Chicken Breast",
                  "quantity": "2 lbs",
                  "category": "Protein",
                  "link": "https://www.tesco.ie/groceries/product/details/some-chicken-link",
                  "protein": "50g",
                  "carbs": "0g",
                  "fats": "5g",
                  "cals": "250"
                }},
                {{
                  "item": "Apple",
                  "quantity": "3",
                  "category": "Produce",
                  "link": "https://www.tesco.ie/groceries/product/details/some-apple-link",
                  "protein": "0.5g",
                  "carbs": "14g",
                  "fats": "0.3g",
                  "cals": "52"
                }}\n              ]\n            }}\n            """
            correction_response = model.generate_content(correction_prompt)
            logger.info(f"Gemini correction response: {correction_response.text}")
            corrected_response_text = correction_response.text.strip()

            json_start_corrected = corrected_response_text.find('{')
            json_end_corrected = corrected_response_text.rfind('}')
            if json_start_corrected != -1 and json_end_corrected != -1:
                final_cleaned_response = corrected_response_text[json_start_corrected : json_end_corrected + 1]
                logger.info(f"Final cleaned corrected grocery response: {final_cleaned_response}")
            else:
                logger.error("Corrected AI response still does not contain a valid JSON object.")
                raise ValueError("Corrected AI response still does not contain a valid JSON object.")
            grocery_list_json = json.loads(final_cleaned_response)
        return grocery_list_json
    except Exception as e:
        logger.error(f"Error extracting grocery list with Gemini via MCP tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Create MCP server from the FastAPI app
mcp_server = FastMCP.from_fastapi(app)

# Mount the MCP server
app.mount("/mcp", mcp_server) # Mount the FastMCP server as an ASGI application

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/mealplan")
async def generate_meal_plan_endpoint(health_data: HealthData):
    print("Received health data:", health_data)
    try:
        # Directly call the tool function
        meal_plan_result = await generate_meal_plan_tool(
            heightFeet=health_data.heightFeet,
            heightInches=health_data.heightInches,
            weight=health_data.weight,
            activityLevel=health_data.activityLevel
        )
        print("Meal plan result from tool:", meal_plan_result)

        if "error" in meal_plan_result:
            raise HTTPException(status_code=500, detail=meal_plan_result["error"])

        return meal_plan_result
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        print("Unexpected error in /mealplan endpoint:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate meal plan: {e}")

@app.post("/grocery-list")
async def create_grocery_list_endpoint(meal_plan: MealPlan):
    try:
        # Directly call the tool function
        grocery_list_result = await extract_grocery_list_tool(meal_plan=meal_plan.dict())
        print("Grocery list result from tool:", grocery_list_result)

        if "error" in grocery_list_result:
            raise HTTPException(status_code=500, detail=grocery_list_result["error"])

        # Generate a session ID and store the grocery list in the database
        session_id = str(uuid.uuid4())
        database.insert_grocery_list(session_id, grocery_list_result)

        return {"session_id": session_id, "grocery_list": grocery_list_result}
    except HTTPException as e:
        raise e
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