# backend/mcp_server.py
import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastapi import FastAPI
import random # Added for mock data in search_walmart_products

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP("walmart-meal-planner")

def _get_gemini_model():
    """Initializes and returns the Gemini model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

@mcp.tool()
async def generate_meal_plan(
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
            The following text was intended to be a JSON object, but it failed to parse.
Please correct it to be a valid JSON object, ensuring it strictly follows the specified format for a meal_plan.
Do not include any conversational text, markdown formatting (like ```json), or extra characters outside the JSON object.

Original problematic text:
{cleaned_response}

Expected JSON format (root object with 'meal_plan' key, which is an array of {days} day objects):
{{
  "meal_plan": [
    {{
      "day": "Monday",
      "breakfast": "...",
      "lunch": "...",
      "dinner": "...",
      "snacks": "..."
    }}
  ]
}}
"""
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
        return {"error": str(e)}

@mcp.tool()
async def extract_grocery_list(meal_plan: dict) -> list:
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
    }}
  ]
}}\n\nEnsure the entire output is a single, valid JSON object without any surrounding text or markdown.\n    """
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
                }}
              ]
            }}\n            """
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
        return {"error": str(e)}

@mcp.tool()
async def search_walmart_products(items: list) -> list:
    """Search for Walmart products based on grocery items."""
    logger.info(f"MCP Tool: search_walmart_products called with items: {items}")
    mock_products = []
    for item in items:
        mock_products.append({
            "item": item,
            "walmart_product_name": f"Mock Walmart {item}",
            "price": round(random.uniform(1.0, 10.0), 2),
            "currency": "USD",
            "link": f"https://www.walmart.com/search?q={item.replace(' ', '+')}"
        })
    return mock_products

# Export the HTTP application provided by FastMCP
mcp_app = mcp.http_app() # Added: Export the FastMCP HTTP application