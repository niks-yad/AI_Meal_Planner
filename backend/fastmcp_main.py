# fastmcp_main.py
import os
import logging
from typing import List
from pydantic import BaseModel, Field
from fastmcp import FastMCP
# from fastmcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from fastapi import FastAPI

# Load env vars
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("MealPlannerMCP")

mcp = FastMCP("MealPlannerMCP")
# mcp = FastMCP("MealPlannerMCP", app=app)

# Pydantic models

class HealthData(BaseModel):
    heightFeet: int = Field(..., ge=0)
    heightInches: int = Field(..., ge=0, le=11)
    weight: int = Field(..., ge=0)  # lbs
    activityLevel: str  # e.g. "sedentary", "light", "moderate", "active"

class DayMeal(BaseModel):
    day: str
    breakfast: str
    lunch: str
    dinner: str
    snacks: str

class MealPlanResponse(BaseModel):
    meal_plan: List[DayMeal]

# Activity level multipliers
activity_multipliers = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very active": 1.9,
}

@mcp.tool()
def calculate_calories_needed(heightFeet: int, heightInches: int, weight: int, activityLevel: str) -> int:
    logger.info(f"Calculating calories needed: {heightFeet}ft {heightInches}in, {weight}lbs, activity: {activityLevel}")

    # Convert height to cm
    height_cm = (heightFeet * 12 + heightInches) * 2.54
    weight_kg = weight * 0.453592

    # Use Mifflin-St Jeor Equation (assuming male for example)
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * 30 + 5  # Age 30 fixed for example

    multiplier = activity_multipliers.get(activityLevel.lower())
    if multiplier is None:
        logger.warning(f"Unknown activity level '{activityLevel}', defaulting to sedentary")
        multiplier = activity_multipliers["sedentary"]

    calories = int(bmr * multiplier)
    logger.info(f"Calculated calories: {calories}")
    return calories

# @mcp.resource("/mealplan")
# def generate_meal_plan(health_data: HealthData, days: int, recipes: List[dict]) -> MealPlanResponse:

@mcp.resource("recipes://{limit}")
def get_recipes(limit: int):
    logger.info(f"Fetching {limit} recipes from Postgres")
    # Postgres connection params from env
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_DB = os.getenv("PG_DB", "mealplanner")
    PG_USER = os.getenv("PG_USER", "user")
    PG_PASS = os.getenv("PG_PASS", "password")

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT data FROM recipes LIMIT %s;", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    recipes = [row["data"] for row in rows]  # assuming JSON blobs in `data` column
    logger.info(f"Fetched {len(recipes)} recipes")
    return recipes

@mcp.prompt()
def generate_meal_plan(health_data: HealthData, days: int, recipes: List[dict]) -> MealPlanResponse:
    logger.info(f"Generating meal plan for {days} days with health data: {health_data}")

    calories = calculate_calories_needed(
        health_data.heightFeet,
        health_data.heightInches,
        health_data.weight,
        health_data.activityLevel,
    )

    prompt = f"""
You are a nutritionist AI. Create a balanced meal plan for {days} days.

User health data:
- Height: {health_data.heightFeet}ft {health_data.heightInches}in
- Weight: {health_data.weight} lbs
- Activity level: {health_data.activityLevel}
- Estimated daily calories: {calories}

Available recipes (JSON format):
{recipes}

Create a meal plan JSON with this structure:
{{
  "meal_plan": [
    {{
      "day": "Monday",
      "breakfast": "...",
      "lunch": "...",
      "dinner": "...",
      "snacks": "..."
    }},
    ...
  ]
}}
"""

    logger.info("Calling Gemini generative AI for meal plan...")
    response = genai.chat.generate(
        model="models/chat-bison-001",
        prompt=prompt,
        temperature=0.7,
        max_output_tokens=1024,
    )
    content = response.text

    try:
        import json
        plan_json = json.loads(content)
        meal_plan_response = MealPlanResponse.parse_obj(plan_json)
        logger.info("Meal plan generated successfully")
        return meal_plan_response
    except Exception as e:
        logger.error(f"Failed to parse meal plan JSON: {e}")
        # Return an empty plan on failure
        return MealPlanResponse(meal_plan=[])

# Expose FastAPI app for uvicorn
app = FastAPI(docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

# Enable CORS for frontend integration
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FastAPI endpoints for frontend integration ---
from fastapi import Body
from fastapi.responses import JSONResponse

@app.post("/mealplan")
async def mealplan_endpoint(
    health_data: HealthData = Body(...),
    days: int = Body(...),
    recipe_limit: int = Body(10)
):
    recipes = mcp.invoke_resource("recipes://{limit}", {"limit": recipe_limit})
    result = generate_meal_plan(health_data, days, recipes)
    return JSONResponse(content=result.dict())

@app.get("/recipes/{limit}")
async def recipes_endpoint(limit: int):
    recipes = mcp.invoke_resource("recipes://{limit}", {"limit": limit})
    return JSONResponse(content={"recipes": recipes})

if __name__ == "__main__":
    logger.info("Starting MealPlannerMCP server...")
    mcp.run()
